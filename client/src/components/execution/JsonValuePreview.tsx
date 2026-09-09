import type { CSSProperties } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";

const MAX_HIGHLIGHTED_JSON_CHARS = 25_000;
const syntax: Record<string, CSSProperties> = {
	'code[class*="language-"]': {
		color: "var(--foreground)",
		fontFamily: "var(--font-mono)",
		textShadow: "none",
		whiteSpace: "pre-wrap",
		overflowWrap: "anywhere",
	},
	'pre[class*="language-"]': {
		color: "var(--foreground)",
		background: "var(--muted)",
		textShadow: "none",
	},
	property: { color: "var(--primary)", fontWeight: 500 },
	string: { color: "var(--foreground)" },
	number: { color: "var(--foreground)", fontWeight: 600 },
	boolean: { color: "var(--foreground)", fontWeight: 600 },
	null: { color: "var(--muted-foreground)" },
	punctuation: { color: "var(--muted-foreground)" },
	operator: { color: "var(--muted-foreground)" },
};

/** Bounded, keyboard-scrollable JSON preview using the active design tokens. */
export function JsonValuePreview({
	value,
	maxHeight = "16rem",
	ariaLabel = "JSON preview",
}: {
	value: unknown;
	maxHeight?: CSSProperties["maxHeight"];
	ariaLabel?: string;
}) {
	const json = JSON.stringify(value, null, 2) ?? "undefined";
	const truncated = json.length > MAX_HIGHLIGHTED_JSON_CHARS;
	return (
		<div className="mt-1 min-w-0 space-y-2">
			{truncated && (
				<p className="text-sm text-muted-foreground">
					Showing the first{" "}
					{MAX_HIGHLIGHTED_JSON_CHARS.toLocaleString()} of{" "}
					{json.length.toLocaleString()} JSON characters. Copy retains
					the full value.
				</p>
			)}
			<div
				role="region"
				aria-label={ariaLabel}
				style={{ maxHeight }}
				tabIndex={0}
				className="min-w-0 max-w-full overflow-auto rounded-[var(--bf-radius-surface)] border border-border bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
			>
				{truncated ? (
					<pre className="whitespace-pre-wrap p-3 font-mono text-sm leading-relaxed text-foreground [overflow-wrap:anywhere]">
						{json.slice(0, MAX_HIGHLIGHTED_JSON_CHARS)}
						{"\n…"}
					</pre>
				) : (
					<SyntaxHighlighter
						language="json"
						style={syntax}
						wrapLongLines
						customStyle={{
							margin: 0,
							padding: "0.75rem",
							fontSize: "0.875rem",
							lineHeight: 1.625,
							overflow: "visible",
							background: "var(--muted)",
						}}
					>
						{json}
					</SyntaxHighlighter>
				)}
			</div>
		</div>
	);
}
