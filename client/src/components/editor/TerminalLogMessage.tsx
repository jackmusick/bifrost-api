import { useNavigate } from "react-router-dom";
import { useEditorStore } from "@/stores/editorStore";

interface TerminalLogMessageProps {
	message: string;
	className?: string;
}

/**
 * Renders a terminal log message with markdown link support
 * Converts [text](url) to clickable links
 */
export function TerminalLogMessage({
	message,
	className,
}: TerminalLogMessageProps) {
	const navigate = useNavigate();
	const minimizeEditor = useEditorStore((state) => state.minimizeEditor);

	// Parse markdown links: [text](url)
	const parts: Array<{
		type: "text" | "link";
		content: string;
		url?: string;
	}> = [];
	const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
	let lastIndex = 0;
	let match;

	while ((match = linkRegex.exec(message)) !== null) {
		// Add text before the link
		if (match.index > lastIndex) {
			parts.push({
				type: "text",
				content: message.substring(lastIndex, match.index),
			});
		}

		// Add the link
		parts.push({
			type: "link",
			content: match[1] || "",
			url: match[2] || "",
		});

		lastIndex = match.index + match[0].length;
	}

	// Add remaining text
	if (lastIndex < message.length) {
		parts.push({
			type: "text",
			content: message.substring(lastIndex),
		});
	}

	// If no links found, just return the text
	if (parts.length === 0) {
		return <span className={className}>{message}</span>;
	}

	const handleClick = (e: React.MouseEvent, url: string) => {
		if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
		e.preventDefault();
		e.stopPropagation();

		// Minimize the editor when navigating away
		minimizeEditor();

		navigate(url);
	};

	return (
		<span className={className}>
			{parts.map((part, index) => {
				if (part.type === "link" && part.url) {
					let url: URL;
					try { url = new URL(part.url, window.location.href); } catch { return <span key={index}>{part.content}</span>; }
					if (!["http:", "https:", "mailto:", "tel:"].includes(url.protocol)) return <span key={index}>{part.content}</span>;
					const internal = url.origin === window.location.origin && ["http:", "https:"].includes(url.protocol);
					const externalPage = !internal && ["http:", "https:"].includes(url.protocol);
					return (
						<a
							key={index}
							href={url.href}
							target={externalPage ? "_blank" : undefined}
							rel={externalPage ? "noopener noreferrer" : undefined}
							onClick={internal ? (e) => handleClick(e, `${url.pathname}${url.search}${url.hash}`) : undefined}
							className="underline text-primary decoration-primary/50 underline-offset-4 hover:decoration-primary rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer"
						>
							{part.content}
							{externalPage && <span className="sr-only"> (opens in a new tab)</span>}
						</a>
					);
				}
				return <span key={index}>{part.content}</span>;
			})}
		</span>
	);
}
