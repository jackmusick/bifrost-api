"""NinjaOne public-IP site-move tracker.

Detects when a managed device has moved to a *different known managed site* (or
has been off all known sites for too long), using the NinjaOne public (WAN
egress) IP as the location signal. Designed to be embedded in another app — these
workflows only compute + persist; they do not deliver (no ticket/email/UI).

Why public IP: `list_devices_detaileds` reports a `publicIP` for ~99% of devices.
Ninja's `locationId` is a *static registration*, not where the device currently
is, so it can't be the current-location signal on its own — the WAN IP can.

Signal design (low-noise):
  * A public IP is a "known managed site" if it is server-anchored (an on-prem
    server at that Ninja org/location egresses from it) or dwell-learned (>=K
    stationary devices of that site have held it as their baseline for >=N days).
  * IPs shared across multiple Ninja orgs (ISP/CGNAT/VPN pools) are excluded —
    they can't be attributed to one site.
  * Cloud-hosted servers (AWS/Azure/GCP adapters) are excluded from anchoring;
    their egress IP is a cloud region, not a physical site.
  * We alert on *transitions between known sites* and on stationary devices that
    sit off all known sites past a threshold — never on mere "left home", which
    is normal laptop roaming.

State persists in the global `ninja_device_site_state` table (one row per Ninja
device id) so the temporal signals — actual moves, dwell-based stationarity, and
long absence — work across scheduled runs.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from time import perf_counter

import httpx
from bifrost import workflow, tables
from modules import ninjaone

STATE_TABLE = "ninja_device_site_state"
SERVER_CLASSES = {"WINDOWS_SERVER", "LINUX_SERVER", "MAC_SERVER"}
# Substrings in a NIC's interface/adapter name that mark a cloud-hosted host.
# (Hyper-V is deliberately NOT here — it's common on-prem virtualization.)
CLOUD_ADAPTER_MARKERS = (
    "amazon",
    "aws",
    "elastic network",
    "azure",
    "google",
    "gvnic",
    "gce ",
)
PERSISTED_STATE_FIELDS = {
    "system_name",
    "node_class",
    "ninja_org_id",
    "home_location_id",
    "current_ip",
    "current_ip_since",
    "prev_ip",
    "baseline_ip",
    "off_all_sites_since",
    "last_seen",
    "last_classification",
}


# --------------------------------------------------------------- io resilience
async def _retry(coro_factory, *, attempts=4, base_delay=1.0):
    """Await coro_factory() with exponential backoff on transient transport errors.

    Large NinjaOne list reads and table operations transiently raise
    httpx.ReadError (a TransportError subclass), which otherwise aborts an
    unattended scheduled run. Only transport-level errors are retried — real
    HTTP status / logic errors propagate immediately.
    """
    delay = base_delay
    for attempt in range(1, attempts + 1):
        try:
            return await coro_factory()
        except httpx.TransportError:
            if attempt == attempts:
                raise
            await asyncio.sleep(delay)
            delay *= 2


# ---------------------------------------------------------------- time helpers
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _age_days(value, now=None):
    dt = _parse_iso(value)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    return (now - dt).total_seconds() / 86400.0


def _site_key(org, loc) -> str:
    return f"{org}:{loc}"


# ---------------------------------------------------------------- data loaders
async def _load_devices():
    rows = await _retry(lambda: ninjaone.list_devices_detaileds())
    return [dict(d) for d in (rows or [])]


async def _cloud_device_ids():
    """Ninja device ids whose active adapters look cloud-hosted (excluded from anchoring)."""
    try:
        ni = await _retry(lambda: ninjaone.list_network_interfaces())
    except Exception:
        return set()
    rows = ni.get("results") if isinstance(ni, dict) else ni
    cloud = set()
    for r in rows or []:
        r = dict(r)
        blob = f"{r.get('interfaceName', '')} {r.get('adapterName', '')}".lower()
        if any(marker in blob for marker in CLOUD_ADAPTER_MARKERS):
            did = r.get("deviceId")
            if did is not None:
                cloud.add(did)
    return cloud


async def _load_state():
    """Return device state plus the number of bounded table queries."""
    out: dict[str, dict] = {}
    query_calls = 0
    offset = 0
    while True:
        page = await _retry(lambda: tables.query(STATE_TABLE, limit=500, offset=offset))
        query_calls += 1
        docs = getattr(page, "documents", page) or []
        if not docs:
            break
        for doc in docs:
            did = doc.get("id") if isinstance(doc, dict) else getattr(doc, "id", None)
            data = (
                doc.get("data") if isinstance(doc, dict) else getattr(doc, "data", None)
            )
            if did is None:
                continue
            normalized = dict(data) if data else {}
            out[str(did)] = normalized
        if len(docs) < 500:
            break
        offset += 500
    return out, query_calls


# ------------------------------------------------------------ fingerprint core
def _build_fingerprints(
    devices,
    state,
    cloud_ids,
    dwell_days,
    dwell_min_devices,
    org_ids,
    shared_org_threshold=3,
):
    """Build ip -> {org, sites[], derivation[]} registry of known managed-site IPs."""
    # Distinct orgs currently egressing from each IP. An IP a candidate anchors to
    # but that is *also* used by devices from many orgs is a shared VPN/CGNAT/DC
    # egress pool, not a site — exclude it. Threshold sits in the gap between the
    # true-positive "home site + one visiting device" case (2 orgs) and real pools.
    ip_org_ids: dict[str, set] = {}
    for d in devices:
        ip, org = d.get("publicIP"), d.get("organizationId")
        if not ip or org is None:
            continue
        if org_ids and org not in org_ids:
            continue
        ip_org_ids.setdefault(ip, set()).add(org)

    ip_map: dict[str, dict] = {}

    def note(ip, org, loc, deriv):
        entry = ip_map.setdefault(
            ip, {"orgs": set(), "sites": set(), "derivation": set()}
        )
        entry["orgs"].add(org)
        entry["sites"].add(_site_key(org, loc))
        entry["derivation"].add(deriv)

    # 1. Server anchors — on-prem (non-cloud) servers pin their egress IP to a site.
    for d in devices:
        ip, org, loc = d.get("publicIP"), d.get("organizationId"), d.get("locationId")
        if not ip or org is None or loc is None:
            continue
        if org_ids and org not in org_ids:
            continue
        if d.get("nodeClass") in SERVER_CLASSES and d.get("id") not in cloud_ids:
            note(ip, org, loc, "server_anchor")

    # 2. Dwell-learned — an IP held as baseline by >=K stationary devices of a site.
    tally: dict[tuple, int] = {}
    for data in state.values():
        bip, org, loc = (
            data.get("baseline_ip"),
            data.get("ninja_org_id"),
            data.get("home_location_id"),
        )
        if not bip or org is None or loc is None:
            continue
        if org_ids and org not in org_ids:
            continue
        if (_age_days(data.get("current_ip_since")) or 0) < dwell_days:
            continue
        key = (org, loc, bip)
        tally[key] = tally.get(key, 0) + 1
    for (org, loc, bip), count in tally.items():
        if count >= dwell_min_devices:
            note(bip, org, loc, "dwell")

    # 3. Resolve exclusions. An IP is a shared pool (not a site) if it anchors to
    #    more than one org, OR if devices from >= shared_org_threshold orgs
    #    currently egress from it (a VPN/CGNAT/datacenter pool).
    registry: dict[str, dict] = {}
    shared: list[str] = []
    for ip, entry in ip_map.items():
        if (
            len(entry["orgs"]) > 1
            or len(ip_org_ids.get(ip, ())) >= shared_org_threshold
        ):
            shared.append(ip)
            continue
        registry[ip] = {
            "org": next(iter(entry["orgs"])),
            "sites": sorted(entry["sites"]),
            "derivation": sorted(entry["derivation"]),
        }
    return {"registry": registry, "excluded_shared_ips": sorted(shared)}


# --------------------------------------------------------------- classifier
def _classify(device, prior, registry, now_iso, stationary_days, absence_days):
    ip = device.get("publicIP")
    org = device.get("organizationId")
    home_loc = device.get("locationId")
    home_site = _site_key(org, home_loc)
    prior = prior or {}

    reg = registry.get(ip)
    matched_org = reg["org"] if reg else None
    matched_site = None
    if reg:
        matched_site = home_site if home_site in reg["sites"] else reg["sites"][0]

    home_matched = bool(reg and matched_org == org and home_site in reg["sites"])
    same_client_other_site = bool(reg and matched_org == org and not home_matched)
    diff_client = bool(reg and matched_org is not None and matched_org != org)

    # Transition timing: reset the "since" clock only when the IP actually changes.
    prev_ip = prior.get("current_ip")
    ip_changed = prev_ip is not None and prev_ip != ip
    if prev_ip == ip and prior.get("current_ip_since"):
        current_ip_since = prior["current_ip_since"]
    else:
        current_ip_since = now_iso

    since_age = _age_days(current_ip_since, now=_parse_iso(now_iso))
    stationary = bool(since_age is not None and since_age >= stationary_days)
    baseline_ip = ip if stationary else prior.get("baseline_ip")

    # Off-all-known-sites tracking (for the long-absence signal).
    if reg is not None:
        off_since = None
    else:
        off_since = prior.get("off_all_sites_since") or now_iso
    off_age = _age_days(off_since, now=_parse_iso(now_iso)) if off_since else None

    if home_matched:
        classification = "home"
    elif diff_client:
        classification = "moved_different_client"
    elif same_client_other_site:
        classification = "moved_same_client"
    elif off_since and off_age is not None and off_age >= absence_days and stationary:
        classification = "off_all_sites_over_threshold"
    else:
        classification = "roaming_unknown"

    row = {
        "device_id": device.get("id"),
        "system_name": device.get("systemName"),
        "node_class": device.get("nodeClass"),
        "ninja_org_id": org,
        "home_location_id": home_loc,
        "current_ip": ip,
        "current_ip_since": current_ip_since,
        "prev_ip": prev_ip if ip_changed else prior.get("prev_ip"),
        "baseline_ip": baseline_ip,
        "stationary": stationary,
        "matched_site": matched_site,
        "matched_org": matched_org,
        "home_matched": home_matched,
        "off_all_sites_since": off_since,
        "last_classification": classification,
        "last_seen": now_iso,
        "updated_at": now_iso,
        "ip_changed_this_run": ip_changed,
    }
    return classification, row


# ------------------------------------------------------------------ workflows
@workflow
async def ninja_build_site_fingerprints(
    org_ids=None,
    dwell_days=7,
    dwell_min_devices=2,
    shared_org_threshold=3,
    detect_cloud=True,
    **kwargs,
):
    """Build the known-managed-site public-IP registry (server-anchored + dwell-learned).

    Read-only. Returns the registry plus derivation stats and exclusions so the
    fingerprint set can be inspected before it drives any alerting.
    """
    workflow_started = perf_counter()

    phase_started = perf_counter()
    devices = await _load_devices()
    load_devices_ms = round((perf_counter() - phase_started) * 1000)

    phase_started = perf_counter()
    state, state_query_calls = await _load_state()
    load_state_ms = round((perf_counter() - phase_started) * 1000)

    phase_started = perf_counter()
    cloud_ids = await _cloud_device_ids() if detect_cloud else set()
    load_network_interfaces_ms = round((perf_counter() - phase_started) * 1000)
    org_set = set(org_ids) if org_ids else None

    phase_started = perf_counter()
    fp = _build_fingerprints(
        devices,
        state,
        cloud_ids,
        dwell_days,
        dwell_min_devices,
        org_set,
        shared_org_threshold,
    )
    build_fingerprints_ms = round((perf_counter() - phase_started) * 1000)
    registry = fp["registry"]

    by_derivation: dict[str, int] = {}
    for entry in registry.values():
        for deriv in entry["derivation"]:
            by_derivation[deriv] = by_derivation.get(deriv, 0) + 1

    return {
        "generated_at": _now_iso(),
        "known_site_ip_count": len(registry),
        "by_derivation": by_derivation,
        "excluded_shared_ip_count": len(fp["excluded_shared_ips"]),
        "excluded_shared_ips": fp["excluded_shared_ips"],
        "cloud_hosted_device_count": len(cloud_ids),
        "registry": registry,
        "timings_ms": {
            "load_devices": load_devices_ms,
            "load_state": load_state_ms,
            "state_query_calls": state_query_calls,
            "state_rows": len(state),
            "load_network_interfaces": load_network_interfaces_ms,
            "build_fingerprints": build_fingerprints_ms,
            "workflow": round((perf_counter() - workflow_started) * 1000),
        },
    }


@workflow
async def ninja_scan_device_site_moves(
    org_ids=None,
    dry_run=False,
    stationary_days=14,
    absence_days=14,
    dwell_days=7,
    dwell_min_devices=2,
    shared_org_threshold=3,
    detect_cloud=True,
    **kwargs,
):
    """Scan all devices, classify each vs. the known-site registry, persist state.

    Classifications: home / moved_same_client / moved_different_client /
    roaming_unknown / off_all_sites_over_threshold. Upserts one row per device to
    `ninja_device_site_state` unless dry_run=True. Returns a summary + the notable
    (actionable) devices for the consuming app to render/deliver.
    """
    workflow_started = perf_counter()
    now_iso = _now_iso()

    phase_started = perf_counter()
    devices = await _load_devices()
    load_devices_ms = round((perf_counter() - phase_started) * 1000)

    phase_started = perf_counter()
    state, state_query_calls = await _load_state()
    load_state_ms = round((perf_counter() - phase_started) * 1000)

    phase_started = perf_counter()
    cloud_ids = await _cloud_device_ids() if detect_cloud else set()
    load_network_interfaces_ms = round((perf_counter() - phase_started) * 1000)
    org_set = set(org_ids) if org_ids else None

    phase_started = perf_counter()
    fp = _build_fingerprints(
        devices,
        state,
        cloud_ids,
        dwell_days,
        dwell_min_devices,
        org_set,
        shared_org_threshold,
    )
    build_fingerprints_ms = round((perf_counter() - phase_started) * 1000)
    registry = fp["registry"]

    summary: dict[str, int] = {}
    notable: list[dict] = []
    upserts: list[dict] = []

    phase_started = perf_counter()
    for d in devices:
        org = d.get("organizationId")
        if org_set and org not in org_set:
            continue
        if not d.get("publicIP"):
            continue
        prior = state.get(str(d.get("id")))
        classification, row = _classify(
            d, prior, registry, now_iso, stationary_days, absence_days
        )
        summary[classification] = summary.get(classification, 0) + 1
        upserts.append(
            {
                "id": str(d.get("id")),
                "data": {key: row[key] for key in PERSISTED_STATE_FIELDS},
            }
        )

        is_move = classification in (
            "moved_same_client",
            "moved_different_client",
            "off_all_sites_over_threshold",
        )
        if is_move or (row["ip_changed_this_run"] and row["matched_site"]):
            notable.append(
                {
                    k: row[k]
                    for k in (
                        "device_id",
                        "system_name",
                        "node_class",
                        "ninja_org_id",
                        "home_location_id",
                        "current_ip",
                        "prev_ip",
                        "matched_site",
                        "matched_org",
                        "last_classification",
                        "stationary",
                    )
                }
            )
    classify_devices_ms = round((perf_counter() - phase_started) * 1000)

    phase_started = perf_counter()
    if not dry_run and upserts:
        for i in range(0, len(upserts), 1000):
            chunk = upserts[i : i + 1000]
            await _retry(lambda c=chunk: tables.bulk_upsert(STATE_TABLE, c))
    persist_state_ms = round((perf_counter() - phase_started) * 1000)

    notable.sort(
        key=lambda n: (
            n["last_classification"] != "moved_different_client",
            n["ninja_org_id"] or 0,
        )
    )

    return {
        "generated_at": now_iso,
        "dry_run": dry_run,
        "devices_scanned": len(upserts),
        "known_site_ip_count": len(registry),
        "excluded_shared_ip_count": len(fp["excluded_shared_ips"]),
        "cloud_hosted_device_count": len(cloud_ids),
        "summary": summary,
        "notable_count": len(notable),
        "notable": notable,
        "timings_ms": {
            "load_devices": load_devices_ms,
            "load_state": load_state_ms,
            "state_query_calls": state_query_calls,
            "state_rows": len(state),
            "load_network_interfaces": load_network_interfaces_ms,
            "build_fingerprints": build_fingerprints_ms,
            "classify_devices": classify_devices_ms,
            "persist_state": persist_state_ms,
            "workflow": round((perf_counter() - workflow_started) * 1000),
        },
    }
