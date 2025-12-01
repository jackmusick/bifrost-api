/**
 * Conflict resolution widgets for Monaco editor
 * Uses zone widgets to insert action links between lines without overlapping
 */
import * as monaco from "monaco-editor";
import {
	detectConflicts,
	acceptCurrent,
	acceptIncoming,
	acceptBoth,
	type ConflictRegion,
} from "./conflictDetector";

class ConflictActionsZoneWidget implements monaco.editor.IViewZone {
	public domNode: HTMLElement;
	public afterLineNumber: number;
	public heightInPx: number;

	constructor(
		private readonly editor: monaco.editor.IStandaloneCodeEditor,
		private readonly conflict: ConflictRegion,
		private readonly onResolve: (newContent: string) => void,
	) {
		this.afterLineNumber = conflict.startLine; // Insert after the line before conflict marker
		this.heightInPx = 20; // Height of the widget
		this.domNode = this.createDomNode();
	}

	private createDomNode(): HTMLElement {
		const container = document.createElement("div");
		container.className = "conflict-actions-zone";
		container.style.cssText = `
			display: flex;
			gap: 0;
			padding: 2px 0;
			margin: 0;
			font-size: 12px;
			font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
			white-space: nowrap;
			align-items: center;
			background: transparent;
			height: 20px;
			line-height: 20px;
			position: relative;
			z-index: 10;
		`;

		const createLink = (text: string, onClick: () => void) => {
			const link = document.createElement("a");
			link.textContent = text;
			link.className = "conflict-action-link";
			link.style.cssText = `
				padding: 2px 4px;
				margin: 0;
				border: none;
				background: none;
				cursor: pointer;
				font-size: 12px;
				color: rgba(100, 100, 100, 0.8);
				text-decoration: none;
				white-space: nowrap;
				display: inline-block;
			`;

			// Use addEventListener instead of onmouseenter/onmouseleave
			link.addEventListener("mouseenter", () => {
				link.style.color = "rgba(60, 60, 60, 1)";
				link.style.textDecoration = "underline";
			});

			link.addEventListener("mouseleave", () => {
				link.style.color = "rgba(100, 100, 100, 0.8)";
				link.style.textDecoration = "none";
			});

			link.addEventListener("click", (e) => {
				e.preventDefault();
				e.stopPropagation();
				onClick();
			});

			return link;
		};

		const createSeparator = () => {
			const separator = document.createElement("span");
			separator.textContent = " | ";
			separator.style.cssText = `
				color: rgba(100, 100, 100, 0.5);
				margin: 0;
				padding: 0;
				user-select: none;
			`;
			return separator;
		};

		container.appendChild(
			createLink("Accept Current Change", () =>
				this.handleAcceptCurrent(),
			),
		);
		container.appendChild(createSeparator());
		container.appendChild(
			createLink("Accept Incoming Change", () =>
				this.handleAcceptIncoming(),
			),
		);
		container.appendChild(createSeparator());
		container.appendChild(
			createLink("Accept Both Changes", () => this.handleAcceptBoth()),
		);

		return container;
	}

	private handleAcceptCurrent() {
		const model = this.editor.getModel();
		if (!model) return;

		const content = model.getValue();
		const resolved = acceptCurrent(content, this.conflict);
		this.onResolve(resolved);
	}

	private handleAcceptIncoming() {
		const model = this.editor.getModel();
		if (!model) return;

		const content = model.getValue();
		const resolved = acceptIncoming(content, this.conflict);
		this.onResolve(resolved);
	}

	private handleAcceptBoth() {
		const model = this.editor.getModel();
		if (!model) return;

		const content = model.getValue();
		const resolved = acceptBoth(content, this.conflict);
		this.onResolve(resolved);
	}
}

/**
 * Add conflict resolution zone widgets to the editor
 */
export function addConflictWidgets(
	editor: monaco.editor.IStandaloneCodeEditor,
	onResolve: (newContent: string) => void,
	conflictsProvider?: () => ConflictRegion[],
): monaco.IDisposable {
	const zoneIds: string[] = [];

	const updateWidgets = () => {
		// Remove old zones
		editor.changeViewZones((changeAccessor) => {
			zoneIds.forEach((id) => {
				changeAccessor.removeZone(id);
			});
		});
		zoneIds.length = 0;

		// Get conflicts from provider or detect from content
		const model = editor.getModel();
		if (!model) return;

		const conflicts = conflictsProvider
			? conflictsProvider()
			: detectConflicts(model.getValue());

		// Add new zones
		editor.changeViewZones((changeAccessor) => {
			conflicts.forEach((conflict) => {
				const zone = new ConflictActionsZoneWidget(
					editor,
					conflict,
					onResolve,
				);
				const zoneId = changeAccessor.addZone(zone);
				zoneIds.push(zoneId);
			});
		});
	};

	// Initial update
	updateWidgets();

	// Update on content change
	const model = editor.getModel();
	const disposable = model?.onDidChangeContent(() => {
		updateWidgets();
	});

	return {
		dispose: () => {
			editor.changeViewZones((changeAccessor) => {
				zoneIds.forEach((id) => {
					changeAccessor.removeZone(id);
				});
			});
			zoneIds.length = 0;
			disposable?.dispose();
		},
	};
}
