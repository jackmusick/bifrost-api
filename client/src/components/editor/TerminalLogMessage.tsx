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
					return (
						<a
							key={index}
							href={part.url}
							onClick={(e) => handleClick(e, part.url!)}
							className="underline text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 cursor-pointer"
						>
							{part.content}
						</a>
					);
				}
				return <span key={index}>{part.content}</span>;
			})}
		</span>
	);
}
