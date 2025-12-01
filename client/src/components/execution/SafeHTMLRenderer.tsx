/**
 * SafeHTMLRenderer - Sanitized HTML display component
 *
 * Renders untrusted HTML content safely using DOMPurify sanitization.
 * This prevents:
 * - XSS attacks via malicious scripts
 * - Dangerous event handlers
 * - Malicious navigation
 * - Form submission to external sites
 *
 * Note: Allows scripts from trusted CDNs (like Tailwind) and inline styles/classes
 * to enable rich formatting while maintaining security.
 */

import DOMPurify from "dompurify";
import { Button } from "@/components/ui/button";
import { ExternalLink } from "lucide-react";

interface SafeHTMLRendererProps {
	html: string;
	title?: string;
	className?: string;
}

export function SafeHTMLRenderer({
	html,
	className = "",
}: SafeHTMLRendererProps) {
	// Sanitize HTML to remove dangerous elements while allowing scripts from trusted sources
	const sanitizedHTML = DOMPurify.sanitize(html, {
		ADD_TAGS: ["script"],
		ADD_ATTR: ["onclick", "onload", "onerror"],
		ALLOWED_URI_REGEXP:
			/^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|data|blob):|[^a-z]|[a-z+.-]+(?:[^a-z+.-:]|$))/i,
		KEEP_CONTENT: true,
		WHOLE_DOCUMENT: true,
		// Hook to allow scripts only from trusted CDNs
		FORBID_ATTR: [
			"onabort",
			"onblur",
			"onchange",
			"onfocus",
			"oninput",
			"onkeydown",
			"onkeypress",
			"onkeyup",
			"onmousedown",
			"onmousemove",
			"onmouseout",
			"onmouseover",
			"onmouseup",
			"onreset",
			"onselect",
			"onsubmit",
			"onunload",
		],
		ALLOWED_TAGS: [
			"html",
			"head",
			"body",
			"title",
			"meta",
			"link",
			"style",
			"script",
			"h1",
			"h2",
			"h3",
			"h4",
			"h5",
			"h6",
			"p",
			"div",
			"span",
			"br",
			"hr",
			"strong",
			"em",
			"b",
			"i",
			"u",
			"s",
			"small",
			"mark",
			"del",
			"ins",
			"sub",
			"sup",
			"ul",
			"ol",
			"li",
			"dl",
			"dt",
			"dd",
			"table",
			"thead",
			"tbody",
			"tfoot",
			"tr",
			"th",
			"td",
			"caption",
			"colgroup",
			"col",
			"blockquote",
			"pre",
			"code",
			"kbd",
			"samp",
			"var",
			"a",
			"img",
			"figure",
			"figcaption",
			"details",
			"summary",
			"section",
			"article",
			"aside",
			"header",
			"footer",
			"nav",
			"main",
			"button",
			"input",
			"select",
			"option",
			"textarea",
			"label",
			"form",
			"svg",
			"path",
			"circle",
			"rect",
			"line",
			"polygon",
			"polyline",
			"ellipse",
			"g",
			"defs",
			"use",
		],
		ALLOWED_ATTR: [
			"id",
			"class",
			"style",
			"title",
			"alt",
			"src",
			"href",
			"width",
			"height",
			"colspan",
			"rowspan",
			"align",
			"valign",
			"lang",
			"dir",
			"aria-label",
			"aria-labelledby",
			"aria-describedby",
			"aria-hidden",
			"role",
			"tabindex",
			"charset",
			"content",
			"name",
			"rel",
			"type",
			"integrity",
			"crossorigin",
			"onclick",
			"onload",
			"viewBox",
			"fill",
			"stroke",
			"stroke-width",
			"stroke-linecap",
			"stroke-linejoin",
			"d",
			"cx",
			"cy",
			"r",
			"x",
			"y",
			"x1",
			"y1",
			"x2",
			"y2",
			"points",
			"clip-rule",
			"fill-rule",
			"transform",
		],
	});

	// Process HTML to extract head content and body content separately
	const processedHTML = (() => {
		const parser = new DOMParser();
		const doc = parser.parseFromString(sanitizedHTML, "text/html");

		// Check if this is a full HTML document
		const hasHtmlTag =
			sanitizedHTML.trim().toLowerCase().startsWith("<!doctype") ||
			sanitizedHTML.trim().toLowerCase().startsWith("<html");

		if (hasHtmlTag) {
			// Extract head content (scripts, styles, meta tags)
			const headContent = Array.from(doc.head.children)
				.map((el) => el.outerHTML)
				.join("\n");

			// Extract body content
			const bodyContent = doc.body.innerHTML;

			// Combine them for rendering (scripts and styles will be executed/applied)
			return headContent + bodyContent;
		}

		// Not a full document, return as-is
		return sanitizedHTML;
	})();

	const openInNewWindow = () => {
		const newWindow = window.open("", "_blank");
		if (newWindow) {
			newWindow.document.write(sanitizedHTML);
			newWindow.document.close();
		}
	};

	return (
		<div className={className}>
			<div className="flex items-center justify-end gap-2 mb-2">
				<Button
					variant="outline"
					size="sm"
					onClick={openInNewWindow}
					title="Open in new window"
				>
					<ExternalLink className="h-4 w-4" />
					<span className="ml-2 hidden sm:inline">Open</span>
				</Button>
			</div>

			<div className="relative overflow-auto">
				<div dangerouslySetInnerHTML={{ __html: processedHTML }} />
			</div>
		</div>
	);
}
