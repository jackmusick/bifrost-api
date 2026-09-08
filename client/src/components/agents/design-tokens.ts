/**
 * Agent-surface roles mapped to the Bifrost design contract in DESIGN.md.
 * Keep exported names stable for existing agent components. Colors follow
 * semantic outcomes independently of tenant branding.
 */

// ──────────────────────────────────────────────────────────────────────────
// Type scale — Bifrost display, interface and measurement roles
// ──────────────────────────────────────────────────────────────────────────

/** Responsive Prompt page title. */
export const TYPE_PAGE_TITLE =
	"font-display text-2xl sm:text-3xl font-semibold leading-tight tracking-tight";

/** 14.5px card / section title — `.card-title` */
export const TYPE_CARD_TITLE = "text-[14.5px] font-semibold";

/** 13.5px body / default — page subtitle, descriptions, nav items */
export const TYPE_BODY = "text-[13.5px]";

/** 13px muted strip — run meta, sidebar body text */
export const TYPE_MUTED = "text-[13px] text-muted-foreground";

/** 12.5px small — button-sm, mono cells, muted inline spans */
export const TYPE_SMALL = "text-[12.5px]";

/** 11.5px uppercase label — `.stat-label` / `.form-section-title` */
export const TYPE_LABEL_UPPERCASE =
	"text-[11.5px] font-medium uppercase tracking-wider text-muted-foreground";

/** Pane label within a workbench column (slightly larger than `TYPE_LABEL_UPPERCASE`). */
export const TYPE_PANE_LABEL =
	"text-xs font-semibold uppercase tracking-wider text-muted-foreground";

/** 22px stat value — `.stat-value` */
export const TYPE_STAT_VALUE =
	"text-[22px] font-semibold leading-tight tracking-tight tabular-nums";

/** 15px mini-stat value — used inside agent grid cards */
export const TYPE_MINI_STAT_VALUE =
	"text-[15px] font-semibold leading-tight tabular-nums";

/** 12px stat delta / helper text */
export const TYPE_STAT_DELTA = "text-[12px]";

/** Mono font family for keys, IDs, hashes — matches `.mono` at 12.5px */
export const TYPE_MONO = "font-mono text-[12.5px]";

// ──────────────────────────────────────────────────────────────────────────
// Gap scale — whitespace between cards/sections
// ──────────────────────────────────────────────────────────────────────────

/** 16px — between cards in a column (`.grid { gap: 16px }`) */
export const GAP_CARD = "gap-4";

/** 12px — between card subsections (header → body, 3-col mini-stat grid) */
export const GAP_SUBSECTION = "gap-3";

/** 6px — between label and value (stat label → stat value) */
export const GAP_LABEL_VALUE = "gap-1.5";

/** 4px — between value and delta line */
export const GAP_VALUE_DELTA = "gap-1";

// ──────────────────────────────────────────────────────────────────────────
// Radius
// ──────────────────────────────────────────────────────────────────────────

/** Ordinary content surface. */
export const RADIUS_CARD = "rounded-[var(--bf-radius-surface)]";

/** Nested content surface. */
export const RADIUS_INNER = "rounded-[var(--bf-radius-surface)]";

/** 6px — small buttons, inputs, tab items */
export const RADIUS_BUTTON = "rounded-[var(--bf-radius-control)]";

// ──────────────────────────────────────────────────────────────────────────
// Card surface — the repeated base container
// ──────────────────────────────────────────────────────────────────────────

/** Inset outline stays visible against bounded scroll-container edges. Add padding separately. */
export const CARD_SURFACE = `${RADIUS_CARD} bg-card ring-1 ring-inset ring-border`;

/** Hover feedback without moving content. */
export const CARD_HOVER =
	"transition-colors duration-[var(--bf-motion-feedback)] hover:ring-primary/40 motion-reduce:transition-none";

/** Card header strip — 14px/16px vertical/horizontal, border-b. */
export const CARD_HEADER = "border-b px-4 py-3";

/** Card body — 16px padding. */
export const CARD_BODY = "p-4";

// ──────────────────────────────────────────────────────────────────────────
// Color tones — delta / tag / icon accent classes
// ──────────────────────────────────────────────────────────────────────────

/** Up/success delta — emerald. */
export const TONE_UP = "text-[var(--bf-success)]";
/** Down/error delta — rose. */
export const TONE_DOWN = "text-[var(--bf-danger)]";
/** Warning — yellow. */
export const TONE_WARN = "text-[var(--bf-warning)]";
/** Muted — default delta tone. */
export const TONE_MUTED = "text-muted-foreground";

/** Status pill — soft green (Active badge). */
export const PILL_ACTIVE =
	"inline-flex items-center gap-1 rounded-[var(--bf-radius-control)] bg-[var(--bf-success)]/10 px-2 py-0.5 text-[11.5px] font-medium text-[var(--bf-success)]";

/** Status pill — soft rose (Failed / flagged). */
export const PILL_ROSE =
	"inline-flex items-center gap-1 rounded-[var(--bf-radius-control)] bg-[var(--bf-danger)]/10 px-2 py-0.5 text-[11.5px] font-medium text-[var(--bf-danger)]";

/** Status pill — soft yellow (Queued / in-progress). */
export const PILL_YELLOW =
	"inline-flex items-center gap-1 rounded-[var(--bf-radius-control)] bg-[var(--bf-warning)]/10 px-2 py-0.5 text-[11.5px] font-medium text-[var(--bf-warning)]";

/** Outlined channel / meta chip — transparent bg, muted text. */
export const CHIP_OUTLINE =
	"inline-flex items-center gap-1 rounded-[var(--bf-radius-control)] border border-border bg-transparent px-2 py-0.5 text-[11.5px] font-medium text-muted-foreground";

// ──────────────────────────────────────────────────────────────────────────
// Color helpers
// ──────────────────────────────────────────────────────────────────────────

/**
 * Success-rate color — emerald / yellow / rose by threshold.
 * Used on sparklines + mini-stat success % across fleet + detail.
 */
export function successRateTone(rate: number): string {
	if (rate >= 0.9) return TONE_UP;
	if (rate >= 0.75) return TONE_WARN;
	return TONE_DOWN;
}
