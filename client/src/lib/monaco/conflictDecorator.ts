/**
 * Monaco conflict decorations and code actions for Git merge conflicts
 */
import * as monaco from "monaco-editor";
import {
	detectConflicts,
	acceptCurrent,
	acceptIncoming,
	acceptBoth,
	type ConflictRegion,
} from "./conflictDetector";
/**
 * Apply conflict decorations to the Monaco editor (client-side parsing)
 */
export function applyConflictDecorations(
	editor: monaco.editor.IStandaloneCodeEditor,
): string[] {
	const model = editor.getModel();
	if (!model) return [];

	const content = model.getValue();
	const conflicts = detectConflicts(content);

	if (conflicts.length === 0) {
		return [];
	}

	const decorations: monaco.editor.IModelDeltaDecoration[] = [];

	for (const conflict of conflicts) {
		// Current changes (HEAD) - green background
		decorations.push({
			range: new monaco.Range(
				conflict.currentStart + 1,
				1,
				conflict.currentEnd + 1,
				Number.MAX_SAFE_INTEGER,
			),
			options: {
				isWholeLine: true,
				className: "conflict-current-content",
				glyphMarginClassName: "conflict-current-glyph",
			},
		});

		// Incoming changes - blue background
		decorations.push({
			range: new monaco.Range(
				conflict.incomingStart + 1,
				1,
				conflict.incomingEnd + 1,
				Number.MAX_SAFE_INTEGER,
			),
			options: {
				isWholeLine: true,
				className: "conflict-incoming-content",
				glyphMarginClassName: "conflict-incoming-glyph",
			},
		});

		// Conflict markers (<<<<<<, =======, >>>>>>>) - gray background
		decorations.push(
			{
				range: new monaco.Range(
					conflict.startLine + 1,
					1,
					conflict.startLine + 1,
					Number.MAX_SAFE_INTEGER,
				),
				options: {
					isWholeLine: true,
					className: "conflict-marker",
				},
			},
			{
				range: new monaco.Range(
					conflict.separatorLine + 1,
					1,
					conflict.separatorLine + 1,
					Number.MAX_SAFE_INTEGER,
				),
				options: {
					isWholeLine: true,
					className: "conflict-marker",
				},
			},
			{
				range: new monaco.Range(
					conflict.endLine + 1,
					1,
					conflict.endLine + 1,
					Number.MAX_SAFE_INTEGER,
				),
				options: {
					isWholeLine: true,
					className: "conflict-marker",
				},
			},
		);
	}

	return editor.deltaDecorations([], decorations);
}

/**
 * Register code actions provider for conflict resolution
 */
export function registerConflictCodeActions(): monaco.IDisposable {
	return monaco.languages.registerCodeActionProvider("*", {
		provideCodeActions(model, range) {
			const content = model.getValue();
			const conflicts = detectConflicts(content);

			// Find conflict at cursor position
			const conflict = conflicts.find(
				(c) =>
					range.startLineNumber >= c.startLine + 1 &&
					range.endLineNumber <= c.endLine + 1,
			);

			if (!conflict) {
				return { actions: [], dispose: () => {} };
			}

			const actions: monaco.languages.CodeAction[] = [
				{
					title: "Accept Current Change",
					kind: "quickfix",
					diagnostics: [],
					edit: {
						edits: [
							{
								resource: model.uri,
								textEdit: {
									range: new monaco.Range(
										conflict.startLine + 1,
										1,
										conflict.endLine + 2,
										1,
									),
									text:
										model
											.getValueInRange(
												new monaco.Range(
													conflict.currentStart + 1,
													1,
													conflict.currentEnd + 1,
													Number.MAX_SAFE_INTEGER,
												),
											)
											.trimEnd() + "\n",
								},
								versionId: model.getVersionId(),
							},
						],
					},
				},
				{
					title: "Accept Incoming Change",
					kind: "quickfix",
					diagnostics: [],
					edit: {
						edits: [
							{
								resource: model.uri,
								textEdit: {
									range: new monaco.Range(
										conflict.startLine + 1,
										1,
										conflict.endLine + 2,
										1,
									),
									text:
										model
											.getValueInRange(
												new monaco.Range(
													conflict.incomingStart + 1,
													1,
													conflict.incomingEnd + 1,
													Number.MAX_SAFE_INTEGER,
												),
											)
											.trimEnd() + "\n",
								},
								versionId: model.getVersionId(),
							},
						],
					},
				},
				{
					title: "Accept Both Changes",
					kind: "quickfix",
					diagnostics: [],
					edit: {
						edits: [
							{
								resource: model.uri,
								textEdit: {
									range: new monaco.Range(
										conflict.startLine + 1,
										1,
										conflict.endLine + 2,
										1,
									),
									text:
										model
											.getValueInRange(
												new monaco.Range(
													conflict.currentStart + 1,
													1,
													conflict.currentEnd + 1,
													Number.MAX_SAFE_INTEGER,
												),
											)
											.trimEnd() +
										"\n" +
										model
											.getValueInRange(
												new monaco.Range(
													conflict.incomingStart + 1,
													1,
													conflict.incomingEnd + 1,
													Number.MAX_SAFE_INTEGER,
												),
											)
											.trimEnd() +
										"\n",
								},
								versionId: model.getVersionId(),
							},
						],
					},
				},
			];

			return {
				actions,
				dispose: () => {},
			};
		},
	});
}

/**
 * Register code lens provider for inline conflict resolution buttons
 */
export function registerConflictCodeLens(
	editor: monaco.editor.IStandaloneCodeEditor,
	onResolve: (newContent: string) => void,
): monaco.IDisposable {
	const model = editor.getModel();
	editor.addCommand(
		0,
		(_ctx, ...args) => {
			const model = args[0] as monaco.editor.ITextModel;
			const conflict = args[1] as ConflictRegion;
			const content = model.getValue();
			const resolved = acceptCurrent(content, conflict);
			onResolve(resolved);
		},
		"conflict.acceptCurrent",
	);

	editor.addCommand(
		0,
		(_ctx, ...args) => {
			const model = args[0] as monaco.editor.ITextModel;
			const conflict = args[1] as ConflictRegion;
			const content = model.getValue();
			const resolved = acceptIncoming(content, conflict);
			onResolve(resolved);
		},
		"conflict.acceptIncoming",
	);

	editor.addCommand(
		0,
		(_ctx, ...args) => {
			const model = args[0] as monaco.editor.ITextModel;
			const conflict = args[1] as ConflictRegion;
			const content = model.getValue();
			const resolved = acceptBoth(content, conflict);
			onResolve(resolved);
		},
		"conflict.acceptBoth",
	);

	// Register for multiple common languages + plaintext explicitly
	const languages = [
		"plaintext",
		"javascript",
		"typescript",
		"python",
		"json",
		"markdown",
		"yaml",
		"xml",
		"html",
		"css",
	];

	const disposable = monaco.languages.registerCodeLensProvider(languages, {
		provideCodeLenses(model) {
			const content = model.getValue();
			const conflicts = detectConflicts(content);
			const lenses: monaco.languages.CodeLens[] = [];

			for (const conflict of conflicts) {
				// Add code lens above the conflict start marker
				lenses.push(
					{
						range: new monaco.Range(
							conflict.startLine + 1,
							1,
							conflict.startLine + 1,
							1,
						),
						command: {
							id: "conflict.acceptCurrent",
							title: "Accept Current Change",
							arguments: [model, conflict],
						},
					},
					{
						range: new monaco.Range(
							conflict.startLine + 1,
							1,
							conflict.startLine + 1,
							1,
						),
						command: {
							id: "conflict.acceptIncoming",
							title: "Accept Incoming Change",
							arguments: [model, conflict],
						},
					},
					{
						range: new monaco.Range(
							conflict.startLine + 1,
							1,
							conflict.startLine + 1,
							1,
						),
						command: {
							id: "conflict.acceptBoth",
							title: "Accept Both Changes",
							arguments: [model, conflict],
						},
					},
				);
			}

			return { lenses, dispose: () => {} };
		},
		resolveCodeLens(_model, codeLens) {
			return codeLens;
		},
	});

	// Manually trigger code lens computation
	if (model) {
		// Force Monaco to recompute code lenses by updating the editor's configuration
		editor.updateOptions({});
	}

	return disposable;
}
