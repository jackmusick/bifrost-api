/**
 * Conflict detection and parsing for Git merge conflicts in Monaco editor
 */

export interface ConflictRegion {
	startLine: number;
	endLine: number;
	currentStart: number;
	currentEnd: number;
	incomingStart: number;
	incomingEnd: number;
	separatorLine: number;
	currentContent: string;
	incomingContent: string;
	ancestor?: string;
}

const CONFLICT_START = /^<{7} (.+)$/;
const CONFLICT_SEPARATOR = /^={7}$/;
const CONFLICT_END = /^>{7} (.+)$/;
const CONFLICT_ANCESTOR = /^\|{7} (.+)$/;

/**
 * Detect and parse Git conflict markers in file content
 */
export function detectConflicts(content: string): ConflictRegion[] {
	const lines = content.split("\n");
	const conflicts: ConflictRegion[] = [];
	let i = 0;

	while (i < lines.length) {
		const line = lines[i];
		if (!line) {
			i++;
			continue;
		}
		const startMatch = line.match(CONFLICT_START);

		if (startMatch) {
			// Found start of conflict
			const startLine = i;
			const currentStart = i + 1;
			let separatorLine = -1;
			let ancestorLine = -1;
			let endLine = -1;

			// Find separator and end
			i++;
			while (i < lines.length) {
				const currentLine = lines[i];
				if (!currentLine) {
					i++;
					continue;
				}
				if (currentLine.match(CONFLICT_SEPARATOR)) {
					separatorLine = i;
				} else if (currentLine.match(CONFLICT_ANCESTOR)) {
					ancestorLine = i;
				} else if (currentLine.match(CONFLICT_END)) {
					endLine = i;
					break;
				}
				i++;
			}

			if (separatorLine !== -1 && endLine !== -1) {
				// Valid conflict found
				const currentEnd = separatorLine - 1;
				const incomingStart = separatorLine + 1;
				const incomingEnd = endLine - 1;

				const currentContent = lines
					.slice(currentStart, separatorLine)
					.join("\n");
				const incomingContent = lines
					.slice(incomingStart, endLine)
					.join("\n");

				const conflict: ConflictRegion = {
					startLine,
					endLine,
					currentStart,
					currentEnd,
					incomingStart,
					incomingEnd,
					separatorLine,
					currentContent,
					incomingContent,
				};

				if (ancestorLine !== -1) {
					conflict.ancestor = lines
						.slice(ancestorLine + 1, separatorLine)
						.join("\n");
				}

				conflicts.push(conflict);
			}
		}

		i++;
	}

	return conflicts;
}

/**
 * Check if content has any merge conflicts
 */
export function hasConflicts(content: string): boolean {
	return (
		content.includes("<<<<<<<") &&
		content.includes("=======") &&
		content.includes(">>>>>>>")
	);
}

/**
 * Clean conflict content by removing all marker lines
 */
function cleanConflictContent(content: string): string[] {
	return content.split("\n").filter((line) => {
		const trimmed = line.trim();
		// Remove lines that are markers or contain markers
		return (
			!trimmed.match(/^<{7}/) &&
			!trimmed.match(/^={7}/) &&
			!trimmed.match(/^>{7}/) &&
			!trimmed.includes("=======") &&
			!trimmed.includes("<<<<<<<") &&
			!trimmed.includes(">>>>>>>")
		);
	});
}

/**
 * Resolve conflict by accepting current changes
 */
export function acceptCurrent(
	content: string,
	conflict: ConflictRegion,
): string {
	const lines = content.split("\n");
	const before = lines.slice(0, conflict.startLine);
	const after = lines.slice(conflict.endLine + 1);

	// Clean the current content
	const currentLines = cleanConflictContent(conflict.currentContent);

	return [...before, ...currentLines, ...after].join("\n");
}

/**
 * Resolve conflict by accepting incoming changes
 */
export function acceptIncoming(
	content: string,
	conflict: ConflictRegion,
): string {
	const lines = content.split("\n");
	const before = lines.slice(0, conflict.startLine);
	const after = lines.slice(conflict.endLine + 1);

	// Clean the incoming content
	const incomingLines = cleanConflictContent(conflict.incomingContent);

	return [...before, ...incomingLines, ...after].join("\n");
}

/**
 * Resolve conflict by accepting both changes
 */
export function acceptBoth(content: string, conflict: ConflictRegion): string {
	const lines = content.split("\n");
	const before = lines.slice(0, conflict.startLine);
	const after = lines.slice(conflict.endLine + 1);

	// Clean both contents
	const currentLines = cleanConflictContent(conflict.currentContent);
	const incomingLines = cleanConflictContent(conflict.incomingContent);

	return [...before, ...currentLines, ...incomingLines, ...after].join("\n");
}
