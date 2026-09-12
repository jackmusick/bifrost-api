/**
 * A single worked-example policy in a reference panel: heading + description +
 * a read-only code view that defaults to YAML with a JSON/YAML toggle, plus a
 * Copy button that copies whatever format is currently shown. Shared by the
 * Tables and Files policy reference panels so examples match the editors
 * (which default to YAML).
 */

import { useEffect, useState } from "react";
import * as yaml from "js-yaml";
import { Button } from "@/components/ui/button";
import { CodeEditor } from "@/components/tables/CodeEditor";

type Format = "yaml" | "json";

export interface PolicyExampleBlockProps {
	heading: string;
	description: string;
	/** The policy document to render (any JSON-serializable shape). */
	policy: unknown;
	/** Stable index for the Monaco model path (must be unique on the page). */
	index: number;
}

function serialize(policy: unknown, format: Format): string {
	return format === "yaml"
		? yaml.dump(policy)
		: JSON.stringify(policy, null, 2);
}

export function PolicyExampleBlock({
	heading,
	description,
	policy,
	index,
}: PolicyExampleBlockProps) {
	const [format, setFormat] = useState<Format>("yaml");
	const [copyStatus, setCopyStatus] = useState<
		"idle" | "copying" | "copied" | "error"
	>("idle");
	const text = serialize(policy, format);

	useEffect(() => {
		if (copyStatus !== "copied") return;
		const timer = setTimeout(() => setCopyStatus("idle"), 1500);
		return () => clearTimeout(timer);
	}, [copyStatus]);

	async function handleCopy() {
		if (copyStatus === "copying") return;
		setCopyStatus("copying");
		try {
			if (!navigator.clipboard?.writeText)
				throw new Error("Clipboard unavailable");
			await navigator.clipboard.writeText(text);
			setCopyStatus("copied");
		} catch {
			setCopyStatus("error");
		}
	}

	function changeFormat(next: Format) {
		setFormat(next);
		setCopyStatus("idle");
	}

	return (
		<div className="min-w-0 space-y-2">
			<div className="flex flex-wrap items-center justify-between gap-2">
				<h5 className="min-w-0 font-mono text-sm font-semibold [overflow-wrap:anywhere]">
					{heading}
				</h5>
				<div className="flex flex-wrap items-center gap-1">
					<div className="flex overflow-hidden rounded-[var(--bf-radius-control)] border text-[11px]">
						<button
							type="button"
							onClick={() => changeFormat("yaml")}
							disabled={copyStatus === "copying"}
							aria-pressed={format === "yaml"}
							className={
								"min-h-11 min-w-11 px-2 py-0.5 transition-colors duration-[var(--bf-motion-feedback)] motion-reduce:transition-none sm:min-h-8 " +
								(format === "yaml"
									? "bg-muted font-medium text-foreground"
									: "text-muted-foreground")
							}
						>
							YAML
						</button>
						<button
							type="button"
							onClick={() => changeFormat("json")}
							disabled={copyStatus === "copying"}
							aria-pressed={format === "json"}
							className={
								"min-h-11 min-w-11 px-2 py-0.5 transition-colors duration-[var(--bf-motion-feedback)] motion-reduce:transition-none sm:min-h-8 " +
								(format === "json"
									? "bg-muted font-medium text-foreground"
									: "text-muted-foreground")
							}
						>
							JSON
						</button>
					</div>
					<Button
						type="button"
						variant="ghost"
						size="xs"
						className="min-h-11 min-w-11 sm:min-h-8"
						onClick={handleCopy}
						aria-label={`Copy ${heading} as ${format.toUpperCase()}`}
						disabled={copyStatus === "copying"}
					>
						{copyStatus === "copying"
							? "Copying…"
							: copyStatus === "copied"
								? "Copied!"
								: "Copy"}
					</Button>
				</div>
			</div>
			<p className="text-xs text-muted-foreground">{description}</p>
			{copyStatus === "error" && (
				<p role="alert" className="text-xs leading-5 text-destructive">
					Could not copy. Select and copy the example text, or try
					again.
				</p>
			)}
			<span role="status" className="sr-only">
				{copyStatus === "copied"
					? `${format.toUpperCase()} copied to clipboard.`
					: ""}
			</span>
			<CodeEditor
				mode={format}
				text={text}
				onChange={() => {}}
				path={`example-${index}.${format}`}
				height="170px"
				readOnly
			/>
		</div>
	);
}
