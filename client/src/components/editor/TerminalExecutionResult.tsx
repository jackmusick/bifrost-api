import { useRef, useState } from "react";
import { useExecutionResult } from "@/hooks/useExecutions";
import { FileText, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TerminalResultModal } from "./TerminalResultModal";
import { useNavigate } from "react-router-dom";

interface TerminalExecutionResultProps {
	executionId: string;
	status: string;
}

export function TerminalExecutionResult({ executionId, status }: TerminalExecutionResultProps) {
	const [showHtmlModal, setShowHtmlModal] = useState(false);
	const navigate = useNavigate();
	const htmlTrigger = useRef<HTMLButtonElement>(null);
	const isComplete = ["Success", "Failed", "CompletedWithErrors", "Timeout", "Cancelled"].includes(status);
	const { data, isLoading, isError, isFetching, refetch } = useExecutionResult(executionId, isComplete);
	if (!isComplete) return null;
	if (isLoading) return <p role="status" className="mt-2 text-sm text-muted-foreground">Loading result…</p>;
	// The result endpoint exposes an untyped object in the generated schema.
	const resultData = data as { result?: unknown; result_type?: string | null } | undefined;
	const result = resultData?.result;
	const notice = isError ? <div role="alert" className="space-y-2 rounded-[var(--bf-radius-control)] bg-[var(--bf-warning-soft)] p-3 text-sm">
		<p>Could not load the latest result.</p>
		<Button variant="outline" className="min-h-11" disabled={isFetching} onClick={() => void refetch()}>{isFetching ? "Retrying…" : "Retry result"}</Button>
	</div> : null;
	if (result === null || result === undefined) return notice;
	if (resultData?.result_type === "html" && typeof result === "string") {
		return <div className="mt-2 min-w-0 space-y-2">
			{notice}
			<Button ref={htmlTrigger} variant="outline" className="min-h-11 whitespace-normal" onClick={() => setShowHtmlModal(true)}><FileText aria-hidden="true" className="size-4" />View HTML result</Button>
			<TerminalResultModal returnFocusRef={htmlTrigger} open={showHtmlModal} onOpenChange={setShowHtmlModal} html={result} executionId={executionId} />
		</div>;
	}
	const text = typeof result === "object" ? JSON.stringify(result, null, 2) : String(result);
	const lines = text.split("\n");
	const hasMore = lines.length > 10;
	return <div className="mt-2 min-w-0 space-y-2">
		{notice}
		<pre role="region" aria-label="Execution result preview" tabIndex={0} className="max-h-[200px] min-w-0 overflow-auto whitespace-pre-wrap rounded-[var(--bf-radius-control)] border bg-muted/50 p-3 font-mono text-sm leading-relaxed [overflow-wrap:anywhere] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring">{lines.slice(0, 10).join("\n")}{hasMore && "\n…"}</pre>
		{hasMore && <Button variant="outline" className="min-h-11 whitespace-normal" onClick={() => navigate(`/history/${executionId}`)}><ExternalLink aria-hidden="true" className="size-4" />View full result</Button>}
	</div>;
}
