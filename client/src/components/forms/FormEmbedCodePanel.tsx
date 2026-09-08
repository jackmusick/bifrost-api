import { useId, useRef, useState } from "react";
import { Copy } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { Button } from "@/components/ui/button";
import { copyToClipboard } from "@/lib/clipboard";

const syntaxStyle = {
	'code[class*="language-"]': { color: "var(--foreground)", fontFamily: "var(--font-mono)" },
	'pre[class*="language-"]': { color: "var(--foreground)", background: "transparent" },
	tag: { color: "var(--foreground)" },
	punctuation: { color: "var(--muted-foreground)" },
	"attr-name": { fontWeight: 600 },
};

export function FormEmbedCodePanel({ code }: { code: string }) {
	const titleId = useId();
	const pending = useRef(false);
	const [result, setResult] = useState<{ code: string; state: "copying" | "copied" | "error" } | null>(null);
	const copy = async () => {
		if (pending.current) return;
		pending.current = true;
		setResult({ code, state: "copying" });
		try {
			setResult({ code, state: await copyToClipboard(code) ? "copied" : "error" });
		} catch {
			setResult({ code, state: "error" });
		} finally {
			pending.current = false;
		}
	};
	const state = result?.code === code ? result.state : null;
	return (
		<section aria-labelledby={titleId} className="min-w-0 overflow-hidden rounded-[var(--bf-radius-surface)] border bg-muted/20">
			<div className="flex flex-wrap items-center justify-between gap-2 border-b px-[var(--bf-surface-pad)] py-2">
				<h3 id={titleId} className="text-sm font-medium">Embed Code</h3>
				<Button type="button" variant="outline" className="min-h-11" disabled={result?.state === "copying"} onClick={() => void copy()} aria-label="Copy embed code"><Copy aria-hidden="true" className="size-4" />{state === "copying" ? "Copying…" : "Copy"}</Button>
			</div>
			<div tabIndex={0} aria-label="Embed code source" className="min-w-0 p-[var(--bf-surface-pad)] focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring" onFocus={event => {
				const range = document.createRange();
				range.selectNodeContents(event.currentTarget);
				const selection = window.getSelection();
				selection?.removeAllRanges();
				selection?.addRange(range);
			}}>
				<SyntaxHighlighter language="html" style={syntaxStyle} wrapLongLines codeTagProps={{ style: { whiteSpace: "pre-wrap", overflowWrap: "anywhere" } }} customStyle={{ margin: 0, padding: 0, fontSize: "0.8125rem", lineHeight: 1.6 }}>{code}</SyntaxHighlighter>
			</div>
			{state === "error" && <p role="alert" className="px-[var(--bf-surface-pad)] pb-[var(--bf-surface-pad)] text-sm text-destructive">Could not copy the code. Select it to copy manually, or try again.</p>}
			{state === "copied" && <p role="status" className="px-[var(--bf-surface-pad)] pb-[var(--bf-surface-pad)] text-sm text-muted-foreground">Embed code copied</p>}
		</section>
	);
}
