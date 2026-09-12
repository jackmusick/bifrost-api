import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card, CardContent } from "@/components/ui/card";

interface FormConfirmationProps {
	formId: string;
	markdown: string;
}

function parentOrigin(): string | null {
	if (!document.referrer) return null;
	try {
		const origin = new URL(document.referrer).origin;
		return origin.startsWith("https://") || origin.startsWith("http://")
			? origin
			: null;
	} catch {
		return null;
	}
}

function safeImageSource(src: string | undefined): string | undefined {
	if (!src) return undefined;
	try {
		const url = new URL(src, window.location.origin);
		if (
			url.protocol === "https:" ||
			url.origin === window.location.origin
		) {
			return url.href;
		}
	} catch {
		return undefined;
	}
	return undefined;
}

export function FormConfirmation({ formId, markdown }: FormConfirmationProps) {
	const containerRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		window.scrollTo({
			top: 0,
			behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)")
				.matches
				? "auto"
				: "smooth",
		});
		containerRef.current?.focus({ preventScroll: true });

		const targetOrigin = parentOrigin();
		if (!targetOrigin || window.parent === window) return;

		const notify = (
			type: "bifrost:form-submitted" | "bifrost:form-resize",
		) => {
			window.parent.postMessage(
				{
					type,
					formId,
					...(type === "bifrost:form-resize"
						? { height: document.documentElement.scrollHeight }
						: {}),
				},
				targetOrigin,
			);
		};

		notify("bifrost:form-submitted");
		const observer = new ResizeObserver(() =>
			notify("bifrost:form-resize"),
		);
		observer.observe(document.documentElement);
		return () => observer.disconnect();
	}, [formId]);

	return (
		<div
			ref={containerRef}
			tabIndex={-1}
			role="status"
			aria-live="polite"
			className="min-w-0 flex scroll-mt-4 justify-center focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
		>
			<Card className="min-w-0 w-full max-w-2xl">
				<CardContent className="prose prose-sm min-w-0 max-w-none p-5 sm:p-6 dark:prose-invert">
					<FormConfirmationMarkdown markdown={markdown} />
				</CardContent>
			</Card>
		</div>
	);
}

export function FormConfirmationMarkdown({ markdown }: { markdown: string }) {
	return (
		<div className="markdown-content min-w-0 text-sm leading-6 [overflow-wrap:anywhere] [&_code]:font-mono">
			<ReactMarkdown
				remarkPlugins={[remarkGfm]}
				components={{
					table: ({ children }) => (
						<div
							role="region"
							aria-label="Confirmation table"
							tabIndex={0}
							className="my-4 max-w-full overflow-x-auto rounded-[var(--bf-radius-surface)] border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
						>
							<table className="w-full min-w-96 text-left text-sm">
								{children}
							</table>
						</div>
					),
					th: ({ children, style }) => (
						<th
							style={style}
							className="min-w-32 border-b bg-muted px-3 py-2 font-semibold"
						>
							{children}
						</th>
					),
					td: ({ children, style }) => (
						<td
							style={style}
							className="min-w-32 border-b px-3 py-2 align-top"
						>
							{children}
						</td>
					),
					pre: ({ children }) => (
						<pre
							tabIndex={0}
							aria-label="Confirmation code example"
							className="max-w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
							style={{ borderRadius: "var(--bf-radius-surface)" }}
						>
							{children}
						</pre>
					),
					img: ({ src, alt }) => {
						const safeSrc = safeImageSource(src);
						return safeSrc ? (
							<img
								src={safeSrc}
								alt={alt || ""}
								loading="lazy"
								referrerPolicy="no-referrer"
								className="h-auto max-w-full"
							/>
						) : null;
					},
					a: ({ href, children }) => {
						const external = href?.startsWith("http");
						return (
							<a
								href={href}
								{...(external
									? {
											target: "_blank",
											rel: "noopener noreferrer",
										}
									: {})}
							>
								{children}
							</a>
						);
					},
				}}
			>
				{markdown}
			</ReactMarkdown>
		</div>
	);
}
