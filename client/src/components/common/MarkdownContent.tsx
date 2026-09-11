import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface MarkdownContentProps {
	content: string;
	/** Preview is phrasing-only and noninteractive, safe inside clickable rows. */
	variant?: "compact" | "preview";
	className?: string;
	/** Extensions for domain-specific references; ordinary fields need neither. */
	components?: Components;
	remarkPlugins?: NonNullable<
		ComponentProps<typeof ReactMarkdown>["remarkPlugins"]
	>;
}

const heading = ({ children }: { children?: ReactNode }) => (
	<h4 className="mb-1 mt-3 text-[1em] font-semibold leading-[inherit] first:mt-0">
		{children}
	</h4>
);
const compactComponents: Components = {
	h1: heading,
	h2: heading,
	h3: heading,
	h4: heading,
	h5: heading,
	h6: heading,
	p: ({ children }) => (
		<p className="my-2 first:mt-0 last:mb-0">{children}</p>
	),
	ul: ({ children }) => (
		<ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>
	),
	ol: ({ children }) => (
		<ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>
	),
	blockquote: ({ children }) => (
		<blockquote className="my-2 border-l border-border pl-3 text-muted-foreground">
			{children}
		</blockquote>
	),
	pre: ({ children }) => (
		<pre className="my-2 max-w-full overflow-x-auto rounded-md bg-muted/50 p-3 text-xs leading-5">
			{children}
		</pre>
	),
	code: ({ children }) => (
		<code className="rounded bg-muted/50 px-1 font-mono text-[0.92em]">
			{children}
		</code>
	),
	a: ({ children, href }) => (
		<a href={href} className="text-primary underline underline-offset-2">
			{children}
		</a>
	),
	img: ({ alt }) => <span className="text-muted-foreground">{alt}</span>,
	table: ({ children }) => (
		<div className="my-2 max-w-full overflow-x-auto rounded-md border border-border">
			<table className="w-full min-w-[24rem] text-left text-[inherit] [overflow-wrap:normal] [&_th]:bg-muted/40 [&_th]:px-3 [&_th]:py-2 [&_th]:font-medium [&_td]:border-t [&_td]:border-border [&_td]:px-3 [&_td]:py-2">
				{children}
			</table>
		</div>
	),
};
const inlineBlock = ({ children }: { children?: ReactNode }) => (
	<span>{children} </span>
);
const previewComponents: Components = {
	p: inlineBlock,
	h1: inlineBlock,
	h2: inlineBlock,
	h3: inlineBlock,
	h4: inlineBlock,
	h5: inlineBlock,
	h6: inlineBlock,
	ul: inlineBlock,
	ol: inlineBlock,
	li: inlineBlock,
	blockquote: inlineBlock,
	pre: inlineBlock,
	table: inlineBlock,
	thead: inlineBlock,
	tbody: inlineBlock,
	tr: inlineBlock,
	th: inlineBlock,
	td: inlineBlock,
	a: ({ children }) => <span>{children}</span>,
	section: inlineBlock,
	code: ({ children }) => (
		<span className="font-mono text-[0.92em]">{children}</span>
	),
	img: ({ alt }) => <span>{alt}</span>,
	br: () => <span> </span>,
	hr: () => <span> </span>,
	input: () => null,
};

/** Compact, safe Markdown for product fields, not document/page typography. */
export function MarkdownContent({
	content,
	variant = "compact",
	className,
	components,
	remarkPlugins = [],
}: MarkdownContentProps) {
	const preview = variant === "preview";
	const Wrapper = preview ? "span" : "div";
	return (
		<Wrapper
			className={cn(
				"min-w-0 whitespace-normal [overflow-wrap:anywhere]",
				!preview && "text-sm leading-6",
				className,
			)}
		>
			<ReactMarkdown
				skipHtml
				remarkPlugins={[remarkGfm, ...remarkPlugins]}
				components={{
					...(preview ? previewComponents : compactComponents),
					...components,
				}}
			>
				{content}
			</ReactMarkdown>
		</Wrapper>
	);
}
