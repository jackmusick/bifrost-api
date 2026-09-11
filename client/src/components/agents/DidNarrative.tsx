/**
 * Render summarizer prose without leaking executor identifiers into the
 * normal review surface. Verified `[exact_tool_name]` markers can link to
 * their grouped Activity item; unmatched legacy markers remain ordinary
 * human-readable text instead of pretending to be controls.
 */

import { createContext, useContext, type ReactNode } from "react";
import { MarkdownContent } from "@/components/common/MarkdownContent";

import { cn } from "@/lib/utils";

import {
	activityDomId,
	delegationTarget,
	humanizeToolReference,
	type RunActivityReferenceIndex,
} from "./run-activity";

export interface DidNarrativeProps {
	text: string | null | undefined;
	/** Recorded actions keyed by exact tool name and ordered by occurrence. */
	activityReferences?: Readonly<RunActivityReferenceIndex>;
	onReferencePreview?: (activityId: string | null) => void;
	onReferenceActivate?: (activityId: string) => void;
	/** When true (drawer/sheet variants), use compact spacing. */
	compact?: boolean;
	fallback?: ReactNode;
}

const TOOL_MARKER = /\[([a-zA-Z_][a-zA-Z0-9_.-]*)\]/g;

type NarrativePart =
	{ kind: "text"; value: string } | { kind: "tool"; name: string };

function splitOnMarkers(text: string): NarrativePart[] {
	const parts: NarrativePart[] = [];
	let cursor = 0;
	for (const match of text.matchAll(TOOL_MARKER)) {
		const start = match.index ?? 0;
		if (start > cursor) {
			parts.push({ kind: "text", value: text.slice(cursor, start) });
		}
		parts.push({ kind: "tool", name: match[1] });
		cursor = start + match[0].length;
	}
	if (cursor < text.length) {
		parts.push({ kind: "text", value: text.slice(cursor) });
	}
	return parts;
}

export function DidNarrative({
	text,
	activityReferences,
	onReferencePreview,
	onReferenceActivate,
	compact,
	fallback,
}: DidNarrativeProps) {
	if (!text || !text.trim()) return <>{fallback}</>;
	const markers: NarrativeContextValue["markers"] = [];
	// Transform parsed text only: code and real Markdown links remain intact.
	const activityMarkers = () => (tree: MarkdownNode) => {
		markers.length = 0;
		const occurrenceByTool: Record<string, number> = {};
		const walk = (node: MarkdownNode) => {
			if (
				["link", "linkReference", "code", "inlineCode"].includes(
					node.type,
				)
			)
				return;
			if (!node.children) return;
			node.children = node.children.flatMap((child): MarkdownNode[] => {
				if (child.type !== "text") {
					walk(child);
					return [child];
				}
				return splitOnMarkers(child.value ?? "").map((part) => {
					if (part.kind === "text")
						return { type: "text", value: part.value };
					const occurrence = occurrenceByTool[part.name] ?? 0;
					occurrenceByTool[part.name] = occurrence + 1;
					const id =
						markers.push({
							name: part.name,
							reference:
								activityReferences?.[part.name]?.[occurrence],
						}) - 1;
					return {
						type: "link",
						url: `#bifrost-activity-marker-${id}`,
						children: [{ type: "text", value: part.name }],
					};
				});
			});
		};
		walk(tree);
	};
	return (
		<NarrativeContext.Provider
			value={{ markers, onReferencePreview, onReferenceActivate }}
		>
			<MarkdownContent
				content={text}
				className={compact ? "text-xs" : undefined}
				remarkPlugins={[activityMarkers]}
				components={narrativeComponents}
			/>
		</NarrativeContext.Provider>
	);
}

interface NarrativeContextValue {
	markers: Array<{
		name: string;
		reference?: RunActivityReferenceIndex[string][number];
	}>;
	onReferencePreview?: DidNarrativeProps["onReferencePreview"];
	onReferenceActivate?: DidNarrativeProps["onReferenceActivate"];
}
const NarrativeContext = createContext<NarrativeContextValue>({ markers: [] });
const narrativeComponents = { a: ActivityReferenceLink };

// A stable component type keeps focus/pointer targets intact when hover updates
// the surrounding activity highlight.
function ActivityReferenceLink({
	href,
	children,
}: {
	href?: string;
	children?: ReactNode;
}) {
	const { markers, onReferencePreview, onReferenceActivate } =
		useContext(NarrativeContext);

	const match = href?.match(/^#bifrost-activity-marker-(\d+)$/);
	const marker = match ? markers[Number(match[1])] : undefined;
	const name = marker?.name;
	if (!name)
		return (
			<a
				href={href}
				className="text-primary underline underline-offset-2"
			>
				{children}
			</a>
		);
	const delegated = !!delegationTarget(name);
	const reference = marker?.reference;
	const label = reference?.label ?? humanizeToolReference(name);

	if (!reference || !onReferenceActivate) {
		return (
			<span
				key={name}
				data-slot="activity-reference-label"
				className={cn(
					"inline-flex items-center rounded-[var(--bf-radius-control)] border border-border/70 bg-muted/60 px-2 py-1 font-medium text-foreground/80",
					delegated &&
						"border-[var(--bf-info)]/20 bg-[var(--bf-info-soft)] text-[var(--bf-info)]",
				)}
			>
				{label}
			</span>
		);
	}

	return (
		<a
			key={name}
			href={`#${activityDomId(reference.activityId)}`}
			data-slot="activity-reference"
			data-activity-reference-id={reference.activityId}
			aria-label={`Show ${label} in Activity`}
			onMouseEnter={() => onReferencePreview?.(reference.activityId)}
			onMouseLeave={() => onReferencePreview?.(null)}
			onFocus={() => onReferencePreview?.(reference.activityId)}
			onBlur={() => onReferencePreview?.(null)}
			onClick={(event) => {
				event.preventDefault();
				onReferenceActivate(reference.activityId);
			}}
			className={cn(
				"mx-0.5 inline-flex min-h-11 cursor-pointer items-center rounded-[var(--bf-radius-control)] px-2 py-1.5 align-baseline text-[0.92em] font-medium outline-none ring-1 transition-colors motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
				delegated
					? "border-[var(--bf-info)]/20 bg-[var(--bf-info-soft)] text-[var(--bf-info)] ring-[var(--bf-info)]/20 hover:bg-[var(--bf-info-soft)]"
					: "border-[var(--bf-info)]/20 bg-[var(--bf-info-soft)] text-[var(--bf-info)] ring-[var(--bf-info)]/20 hover:bg-[var(--bf-info-soft)]/80",
			)}
		>
			{label}
		</a>
	);
}

interface MarkdownNode {
	type: string;
	value?: string;
	url?: string;
	children?: MarkdownNode[];
}
