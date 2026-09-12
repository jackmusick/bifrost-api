#!/usr/bin/env python3
"""Generate a mechanical UI inventory for the client app.

The script uses only the Python standard library. It scans the React router
tree, page TSX files, shared UI primitives, and feature component files, then
writes:

- docs/design-modernization/inventory.json
- docs/design-modernization/coverage.md

The markdown file is intentionally compact: it carries the route/family ledger
while the JSON file carries the full file inventories.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


WRAPPER_COMPONENTS = {"ProtectedRoute"}
_PAGE_COMPONENT_TO_MODULE: dict[str, str] = {}


@dataclass(frozen=True)
class AssetRecord:
    path: str
    kind: str
    group: str
    source_evidence: str
    destination_rule: str
    behavior_to_preserve: str
    themes: str
    widths: str
    states_interactions: str
    implementation: str
    rendered_proof: str
    status: str


@dataclass(frozen=True)
class RouteRecord:
    path: str | None
    full_path: str
    kind: str
    layout: str
    access: str
    source_file: str
    page_component: str | None
    page_module: str | None
    family: str
    has_loader: bool
    has_error_boundary: bool
    is_index: bool
    is_wildcard: bool
    child_count: int
    status: str
    evidence: str = "Pending"


@dataclass(frozen=True)
class FamilyRecord:
    scope: str
    source_evidence: str
    destination_rule: str
    behavior_to_preserve: str
    themes: str
    widths: str
    states_interactions: str
    implementation: str
    rendered_proof: str
    status: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _client_root(root: Path) -> Path:
    return root / "client"


def _pages_root(client_root: Path) -> Path:
    return client_root / "src" / "pages"


def _components_root(client_root: Path) -> Path:
    return client_root / "src" / "components"


def _app_path(client_root: Path) -> Path:
    return client_root / "src" / "App.tsx"


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _escape_cell(value: str | None) -> str:
    if value is None:
        return "Pending"
    text = value.replace("\n", "<br>")
    return text.replace("|", "\\|")


def _component_name_from_route_tag(tag: str) -> str | None:
    element_value = _extract_braced_attr(tag, "element")
    if not element_value:
        return None
    candidates = re.findall(r"<([A-Z][A-Za-z0-9_]*)\b", element_value)
    for candidate in reversed(candidates):
        if candidate == "Route":
            continue
        if candidate in WRAPPER_COMPONENTS:
            continue
        return candidate
    return None


def _route_tag_end(source: str, start: int) -> int:
    in_string: str | None = None
    escape = False
    brace_depth = 0
    i = start
    while i < len(source):
        ch = source[i]
        if in_string is not None:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
            i += 1
            continue
        if ch in {'"', "'", "`"}:
            in_string = ch
        elif ch == "{":
            brace_depth += 1
        elif ch == "}":
            if brace_depth > 0:
                brace_depth -= 1
        elif ch == ">" and brace_depth == 0:
            return i + 1
        i += 1
    raise ValueError("Unterminated <Route> tag")


def _extract_attr(tag: str, attr: str) -> str | None:
    pattern = rf"\b{re.escape(attr)}\s*=\s*([\"'])(.*?)\1"
    match = re.search(pattern, tag, re.S)
    return match.group(2) if match else None


def _extract_braced_attr(tag: str, attr: str) -> str | None:
    match = re.search(rf"\b{re.escape(attr)}\s*=", tag)
    if not match:
        return None
    brace_start = tag.find("{", match.end())
    if brace_start == -1:
        return None
    depth = 0
    in_string: str | None = None
    escape = False
    for i in range(brace_start + 1, len(tag)):
        ch = tag[i]
        if in_string is not None:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
            continue
        if ch in {'"', "'", "`"}:
            in_string = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            if depth == 0:
                return tag[brace_start + 1 : i]
            depth -= 1
    return None


def _has_attr(tag: str, attr: str) -> bool:
    return re.search(rf"\b{re.escape(attr)}\b", tag) is not None


def _route_nodes(source: str) -> list[dict]:
    token_re = re.compile(r"</?Route\b")

    def parse_range(start: int, stop_at_close: bool) -> tuple[list[dict], int]:
        nodes: list[dict] = []
        i = start
        while i < len(source):
            match = token_re.search(source, i)
            if not match:
                return nodes, len(source)
            token_start = match.start()
            if source.startswith("</Route", token_start):
                close_end = source.find(">", token_start)
                if close_end == -1:
                    raise ValueError("Unterminated </Route> tag")
                if stop_at_close:
                    return nodes, close_end + 1
                i = close_end + 1
                continue

            tag_end = _route_tag_end(source, token_start)
            tag = source[token_start:tag_end]
            node = {
                "tag": tag,
                "path": _extract_attr(tag, "path"),
                "index": _has_attr(tag, "index"),
                "component": _component_name_from_route_tag(tag),
                "loader": _has_attr(tag, "loader"),
                "error_element": _has_attr(tag, "errorElement"),
                "self_closing": tag.rstrip().endswith("/>"),
                "children": [],
            }
            if not node["self_closing"]:
                children, next_index = parse_range(tag_end, True)
                node["children"] = children
                i = next_index
            else:
                i = tag_end
            nodes.append(node)
        return nodes, len(source)

    nodes, _ = parse_range(0, False)
    return nodes


def _join_path(parent: str, child: str | None, is_index: bool) -> str:
    if is_index:
        return parent or "/"
    if not child:
        return parent or "/"
    if child.startswith("/"):
        return child
    if parent in {"", "/"}:
        return "/" + child.lstrip("/")
    if parent.endswith("/"):
        return parent + child.lstrip("/")
    return parent + "/" + child.lstrip("/")


def _route_family(full_path: str, component: str | None, layout: str, access: str) -> str:
    path = full_path.rstrip("/") or "/"
    if path in {"/login", "/setup", "/accept-invite", "/mfa-setup", "/device"}:
        return "auth/public/embedded"
    if path.startswith("/auth/callback/") or path.startswith("/oauth/callback/") or path == "/mcp/callback":
        return "auth/public/embedded"
    if path.startswith("/embedded/forms/"):
        return "form runtime"
    if path == "/execute/:formId" or path.startswith("/execute/"):
        return "form runtime"
    if path == "/forms/new" or path == "/forms/:formId/edit":
        return "form designer"
    if path == "/history/:executionId" or path == "/history" or path == "/workflows/:workflowName/execute":
        return "execution"
    if path.startswith("/agents"):
        return "agent"
    if path in {
        "/settings",
        "/settings/:tab",
        "/user-settings",
        "/user-settings/:tab",
    }:
        return "settings"
    if path in {"/apps/new", "/apps/:applicationId/edit/*"}:
        return "editor"
    if path in {"/apps", "/apps/:applicationId/*", "/apps/:applicationId/preview/*"}:
        return "v1 contract"
    if component in {"Layout", "ContentLayout"}:
        return "shell"
    if path in {
        "/solutions",
        "/solutions/:solutionId",
        "/config",
        "/tables",
        "/tables/:tableId",
        "/files",
        "/knowledge",
        "/entity-management",
        "/integrations",
        "/integrations/:id",
        "/mcp-servers",
        "/mcp-servers/:id",
        "/mcp-servers/:serverId/connections/:connectionId/edit",
        "/event-sources",
        "/event-sources/:sourceId",
        "/event-sources/:sourceId/events/:eventId",
    }:
        return "dependencies"
    if path in {
        "/",
        "/workflows",
        "/forms",
        "/organizations",
        "/users",
        "/users/:userId",
        "/roles",
        "/roles/:roleId",
        "/roles/:roleId/:tab",
        "/diagnostics",
        "/audit",
        "/reports/roi",
        "/reports/usage",
        "/chat/:conversationId?",
        "/chat/artifacts",
    }:
        return "list"
    return "other"


def _flatten_routes(nodes: list[dict], parent_path: str = "", layout: str = "", access: str = "public") -> list[RouteRecord]:
    flat: list[RouteRecord] = []
    for node in nodes:
        component = node["component"]
        next_layout = layout
        if component in {"Layout", "ContentLayout"}:
            next_layout = component
        if _has_attr(node["tag"], "requirePlatformAdmin"):
            next_access = "platform admin"
        elif _has_attr(node["tag"], "requireOrgUser"):
            next_access = "org user"
        elif "ProtectedRoute" in node["tag"]:
            next_access = "authenticated"
        else:
            next_access = "public"

        full_path = _join_path(parent_path, node["path"], node["index"])
        if node["path"] is not None or node["index"]:
            kind = "index" if node["index"] else ("layout-container" if node["children"] else "route")
            page_module = _PAGE_COMPONENT_TO_MODULE.get(component or "", None)
            flat.append(
                RouteRecord(
                    path=node["path"],
                    full_path=full_path,
                    kind=kind,
                    layout=next_layout or ("shell" if full_path == "/" else "none"),
                    access=next_access,
                    source_file="client/src/App.tsx",
                    page_component=component,
                    page_module=page_module,
                    family=_route_family(full_path, component, next_layout, next_access),
                    has_loader=bool(node["loader"]),
                    has_error_boundary=bool(node["error_element"]),
                    is_index=bool(node["index"]),
                    is_wildcard=bool(node["path"] and "*" in node["path"]),
                    child_count=len(node["children"]),
                    status="Pending",
                )
            )
        if node["children"]:
            flat.extend(_flatten_routes(node["children"], full_path, next_layout, next_access))
    return flat


def _collect_lazy_component_map(app_source: str) -> dict[str, str]:
    mapping: dict[str, str] = {}

    # Static route wrappers and layout imports are just as important as lazy pages.
    for match in re.finditer(r'import\s*\{([^}]+)\}\s*from\s*[\"\']([^\"\']+)[\"\']', app_source, re.S):
        for binding in match.group(1).split(","):
            binding = binding.strip()
            if binding:
                mapping[binding.split(" as ")[-1].strip()] = match.group(2)

    direct_pattern = re.compile(
        r'const\s+(\w+)\s*=\s*lazyWithReload\(\(\)\s*=>\s*import\("([^"]+)"\)\.then\(\s*\(\w+\)\s*=>\s*\(\{\s*default:\s*\w+\.(\w+)\s*,?\s*\}\)\s*\)\s*,?\s*\)',
        re.S,
    )
    for match in direct_pattern.finditer(app_source):
        component = match.group(1)
        module = match.group(2)
        mapping[component] = module

    helper_pattern = re.compile(
        r"export\s+const\s+(\w+)\s*=\s*\(\)\s*=>\s*import\(\"([^\"]+)\"\)\.then\(",
        re.S,
    )
    helper_modules: dict[str, str] = {}
    for match in helper_pattern.finditer(app_source):
        helper_modules[match.group(1)] = match.group(2)

    alias_pattern = re.compile(r"const\s+(\w+)\s*=\s*lazyWithReload\((\w+)\s*\)", re.S)
    for match in alias_pattern.finditer(app_source):
        component = match.group(1)
        helper = match.group(2)
        if helper in helper_modules:
            mapping[component] = helper_modules[helper]

    return mapping


def _discover_pages(pages_root: Path, root: Path) -> list[AssetRecord]:
    files: list[AssetRecord] = []
    for path in sorted(pages_root.rglob("*.tsx")):
        if path.name.endswith(".test.tsx"):
            continue
        rel = _rel(path, root)
        parts = path.relative_to(pages_root).parts
        if len(parts) == 1:
            kind = "page"
            group = "top-level"
        elif "components" in parts:
            kind = "page-component"
            group = parts[0]
        else:
            kind = "page-module"
            group = parts[0]
        files.append(
            AssetRecord(
                path=rel,
                kind=kind,
                group=group,
                source_evidence=rel,
                destination_rule="Pending",
                behavior_to_preserve="Pending",
                themes="Pending",
                widths="Pending",
                states_interactions="Pending",
                implementation="Pending",
                rendered_proof="Pending",
                status="Pending",
            )
        )
    return files


def _discover_ui_primitives(components_root: Path, root: Path) -> list[AssetRecord]:
    files: list[AssetRecord] = []
    ui_root = components_root / "ui"
    for path in sorted(ui_root.rglob("*.tsx")):
        if path.name.endswith(".test.tsx"):
            continue
        rel = _rel(path, root)
        files.append(
            AssetRecord(
                path=rel,
                kind="ui-primitive",
                group=path.stem,
                source_evidence=rel,
                destination_rule="Pending",
                behavior_to_preserve="Pending",
                themes="Pending",
                widths="Pending",
                states_interactions="Pending",
                implementation="Pending",
                rendered_proof="Pending",
                status="Pending",
            )
        )
    return files


def _discover_feature_components(components_root: Path, root: Path) -> list[AssetRecord]:
    files: list[AssetRecord] = []
    for path in sorted(components_root.rglob("*.tsx")):
        if path.name.endswith(".test.tsx"):
            continue
        if "/ui/" in path.as_posix():
            continue
        rel = _rel(path, root)
        group = path.relative_to(components_root).parts[0]
        files.append(
            AssetRecord(
                path=rel,
                kind="feature-component",
                group=group,
                source_evidence=rel,
                destination_rule="Pending",
                behavior_to_preserve="Pending",
                themes="Pending",
                widths="Pending",
                states_interactions="Pending",
                implementation="Pending",
                rendered_proof="Pending",
                status="Pending",
            )
        )
    return files


def _load_existing_inventory(out_dir: Path) -> dict:
    inventory_path = out_dir / "inventory.json"
    if not inventory_path.exists():
        return {}
    try:
        return json.loads(inventory_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _merge_existing_rows(
    current_rows: list[dict],
    existing_rows: list[dict] | None,
    key_fields: tuple[str, ...],
) -> list[dict]:
    if not existing_rows:
        return current_rows
    existing_map: dict[tuple[str, ...], dict] = {}
    for row in existing_rows:
        key = tuple(str(row.get(field, "")) for field in key_fields)
        existing_map[key] = row
    merged: list[dict] = []
    for row in current_rows:
        key = tuple(str(row.get(field, "")) for field in key_fields)
        existing = existing_map.get(key)
        if existing:
            new_row = dict(row)
            new_row.update(existing)
            merged.append(new_row)
        else:
            merged.append(row)
    return merged


def _family_rows(routes: list[RouteRecord]) -> list[FamilyRecord]:
    grouped: dict[str, list[str]] = {
        "foundation": [],
        "shell": [],
        "branding": [],
        "v1 contract": [],
        "auth/public/embedded": [],
        "list": [],
        "execution": [],
        "agent": [],
        "form runtime": [],
        "form designer": [],
        "dependencies": [],
        "editor": [],
        "settings": [],
        "other": [],
    }
    for route in routes:
        grouped.setdefault(route.family, []).append(route.full_path)

    def join_paths(name: str) -> str:
        paths = grouped.get(name, [])
        return ", ".join(sorted(dict.fromkeys(paths))) if paths else "Pending"

    return [
        FamilyRecord(
            scope="foundation",
            source_evidence="client/src/index.css; client/src/contexts/ThemeContext.tsx; client/src/main.tsx",
            destination_rule="Pending",
            behavior_to_preserve="Typography, tokens, density, motion, reduced-motion, and theme persistence.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="shell",
            source_evidence="client/src/components/layout/Layout.tsx; client/src/components/layout/AppLayout.tsx; client/src/components/layout/Sidebar.tsx; client/src/components/layout/Header.tsx",
            destination_rule="Pending",
            behavior_to_preserve="Global chrome, navigation, account access, and scroll ownership.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="branding",
            source_evidence="client/src/hooks/useBranding.ts; client/src/lib/branding.ts; client/src/pages/settings/Branding.tsx; client/src/components/branding/Logo.tsx",
            destination_rule="Pending",
            behavior_to_preserve="Product identity, logo treatment, and update messaging.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="v1 contract",
            source_evidence="client/src/pages/AppRouter.tsx; client/src/components/jsx-app/BundledAppShell.tsx; client/src/components/jsx-app/StandaloneV2App.tsx",
            destination_rule="Pending",
            behavior_to_preserve="Published/preview app routing, embed mode, and standalone-v2 full-screen ownership.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="auth/public/embedded",
            source_evidence=join_paths("auth/public/embedded"),
            destination_rule="Pending",
            behavior_to_preserve="Unauthenticated entry points, callback flows, device auth, and embedded form routes.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="list",
            source_evidence=join_paths("list"),
            destination_rule="Pending",
            behavior_to_preserve="Directory-style navigation, tables, filters, and detail-entry affordances.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="execution",
            source_evidence=join_paths("execution"),
            destination_rule="Pending",
            behavior_to_preserve="Run history, execution detail, and workflow execution flow.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="agent",
            source_evidence=join_paths("agent"),
            destination_rule="Pending",
            behavior_to_preserve="Agent fleet, detail, review, tuning, and run detail workflows.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="form runtime",
            source_evidence=join_paths("form runtime"),
            destination_rule="Pending",
            behavior_to_preserve="Form execution, embedded submission, and public/hmac runtime entry points.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="form designer",
            source_evidence=join_paths("form designer"),
            destination_rule="Pending",
            behavior_to_preserve="Create/edit form authoring, builder state, and save flows.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="dependencies",
            source_evidence="client/src/hooks/useDependencyGraph.ts; client/src/components/dependencies/DependencyGraph.tsx; client/src/components/dependencies/EntityNode.tsx; client/src/components/entity-management/DependencyGraphDialog.tsx; client/src/components/dependencies/dependency-graph.css; client/src/pages/EntityManagement.tsx; client/src/pages/Integrations.tsx; client/src/pages/MCPServers.tsx; client/src/pages/Events.tsx; client/src/pages/Knowledge.tsx; client/src/pages/Tables.tsx; client/src/pages/Files.tsx; client/src/pages/Solutions.tsx; client/src/pages/Config.tsx",
            destination_rule="Pending",
            behavior_to_preserve="Dependency-management lists, detail panes, and cross-entity navigation.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="editor",
            source_evidence=join_paths("editor"),
            destination_rule="Pending",
            behavior_to_preserve="App editor, code editor, conflict handling, overlays, and dock interactions.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="settings",
            source_evidence=join_paths("settings"),
            destination_rule="Pending",
            behavior_to_preserve="Platform and user settings tabs, form saves, and destructive updates.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
        FamilyRecord(
            scope="other",
            source_evidence=join_paths("other"),
            destination_rule="Pending",
            behavior_to_preserve="Any route not captured by the named migration families.",
            themes="Pending",
            widths="Pending",
            states_interactions="Pending",
            implementation="Pending",
            rendered_proof="Pending",
            status="Pending",
        ),
    ]


def _route_behavior(route: RouteRecord) -> str:
    path = route.full_path
    if route.kind == "layout-container" and route.page_component == "Layout":
        return "Owns the global application shell and page outlet."
    if route.kind == "layout-container" and route.page_component == "ContentLayout":
        return "Owns the padding-free content layout for chat and execution detail."
    if path == "/":
        return "Primary dashboard landing page."
    if path == "/forms":
        return "Forms list and entry point for creation and execution."
    if path in {"/forms/new", "/forms/:formId/edit"}:
        return "Form builder and form editing."
    if path == "/history":
        return "Execution history list."
    if path == "/history/:executionId":
        return "Execution detail drill-down."
    if path.startswith("/agents"):
        return "Agent fleet, detail, review, tuning, and run detail."
    if path.startswith("/apps"):
        return "App list, editor, preview, and embedded runtime surfaces."
    if path.startswith("/settings") or path.startswith("/user-settings"):
        return "Platform and user settings tabs."
    if path.startswith("/embedded/forms/") or path.startswith("/execute/"):
        return "Form execution and embedded submission."
    if path.startswith("/chat"):
        return "Chat and artifact browser."
    if path.startswith("/reports/"):
        return "Reporting and drill-down views."
    if path.startswith("/mcp-servers") or path.startswith("/integrations") or path.startswith("/event-sources"):
        return "Integration and dependency management."
    return "Pending"


def _route_scope(route: RouteRecord) -> str:
    pieces = [
        route.full_path,
        route.kind,
        route.layout or "none",
        route.access,
        route.page_component or "none",
        route.page_module or "none",
        route.family,
    ]
    return " · ".join(pieces)


def _render_markdown(families: list[FamilyRecord], routes: list[RouteRecord]) -> str:
    lines: list[str] = []
    lines.append("# Design Modernization Coverage Ledger")
    lines.append("")
    lines.append("Generated from the current client source tree. The source inventory lives in `inventory.json`; this file keeps the evidence ledger compact and route-focused.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Routes discovered: {len(routes)}")
    lines.append(f"- Family rows: {len(families)}")
    lines.append("")
    lines.append("## Required Families")
    lines.append("")
    lines.append("| Scope | Source evidence | Destination rule | Behavior to preserve | Themes | Widths | States/interactions | Implementation | Rendered proof | Status/exception |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in families:
        lines.append(
            "| "
            + " | ".join(
                _escape_cell(value)
                for value in [
                    row.scope,
                    row.source_evidence,
                    row.destination_rule,
                    row.behavior_to_preserve,
                    row.themes,
                    row.widths,
                    row.states_interactions,
                    row.implementation,
                    row.rendered_proof,
                    row.status,
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Route Inventory")
    lines.append("")
    lines.append("| Scope | Source evidence | Destination rule | Behavior to preserve | Themes | Widths | States/interactions | Implementation | Rendered proof | Status/exception |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for route in routes:
        lines.append(
            "| "
            + " | ".join(
                _escape_cell(value)
                for value in [
                    _route_scope(route),
                    f"client/src/App.tsx; route `{route.full_path}`",
                    "Pending",
                    _route_behavior(route),
                    "Pending",
                    "Pending",
                    "Pending",
                    "Pending",
                    route.evidence,
                    route.status,
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _to_json(root: Path, routes: list[RouteRecord], pages: list[AssetRecord], ui: list[AssetRecord], feature: list[AssetRecord], families: list[FamilyRecord]) -> dict:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "counts": {
            "routes": len(routes),
            "pages": len(pages),
            "shared_ui_primitives": len(ui),
            "feature_components": len(feature),
            "families": len(families),
        },
        "routes": [asdict(route) for route in routes],
        "pages": [asdict(item) for item in pages],
        "shared_ui_primitives": [asdict(item) for item in ui],
        "feature_components": [asdict(item) for item in feature],
        "families": [asdict(item) for item in families],
    }


def _print_counts(routes: list[RouteRecord], pages: list[AssetRecord], ui: list[AssetRecord], feature: list[AssetRecord]) -> None:
    print(f"routes: {len(routes)}")
    print(f"pages: {len(pages)}")
    print(f"shared ui primitives: {len(ui)}")
    print(f"feature components: {len(feature)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_repo_root(), help="Repository root (defaults to the worktree root).")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory for inventory files (defaults to docs/design-modernization).",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    client_root = _client_root(root)
    pages_root = _pages_root(client_root)
    components_root = _components_root(client_root)
    app_source = _app_path(client_root).read_text(encoding="utf-8")

    global _PAGE_COMPONENT_TO_MODULE
    _PAGE_COMPONENT_TO_MODULE = _collect_lazy_component_map(app_source)

    routes = _flatten_routes(_route_nodes(app_source))
    pages = _discover_pages(pages_root, root)
    ui = _discover_ui_primitives(components_root, root)
    feature = _discover_feature_components(components_root, root)
    families = _family_rows(routes)

    out_dir = (args.out_dir or (root / "docs" / "design-modernization")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    inventory_path = out_dir / "inventory.json"
    coverage_path = out_dir / "coverage.md"

    existing = _load_existing_inventory(out_dir)
    routes_payload = [asdict(route) for route in routes]
    if existing.get("routes"):
        existing_route_map = {
            (str(row.get("full_path", "")), str(row.get("kind", "")), str(row.get("source_file", "")), str(row.get("page_component", ""))): row
            for row in existing["routes"]
        }
        for row in routes_payload:
            key = (str(row.get("full_path", "")), str(row.get("kind", "")), str(row.get("source_file", "")), str(row.get("page_component", "")))
            old = existing_route_map.get(key)
            if old and old.get("status"):
                row["status"] = old["status"]
            if old and old.get("evidence"):
                row["evidence"] = old["evidence"]
    pages_payload = _merge_existing_rows(
        [asdict(item) for item in pages],
        existing.get("pages"),
        ("path",),
    )
    ui_payload = _merge_existing_rows(
        [asdict(item) for item in ui],
        existing.get("shared_ui_primitives"),
        ("path",),
    )
    feature_payload = _merge_existing_rows(
        [asdict(item) for item in feature],
        existing.get("feature_components"),
        ("path",),
    )
    family_payload = _merge_existing_rows(
        [asdict(item) for item in families],
        existing.get("families"),
        ("scope",),
    )
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "counts": {
            "routes": len(routes_payload),
            "pages": len(pages_payload),
            "shared_ui_primitives": len(ui_payload),
            "feature_components": len(feature_payload),
            "families": len(family_payload),
        },
        "routes": routes_payload,
        "pages": pages_payload,
        "shared_ui_primitives": ui_payload,
        "feature_components": feature_payload,
        "families": family_payload,
    }
    inventory_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    coverage_path.write_text(_render_markdown([FamilyRecord(**row) for row in family_payload], [RouteRecord(**row) for row in routes_payload]), encoding="utf-8")

    _print_counts(routes, pages, ui, feature)
    print(f"wrote {inventory_path}")
    print(f"wrote {coverage_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
