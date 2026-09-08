import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import {
	AlertTriangle,
	AppWindow,
	Bot,
	Database,
	FileCode,
	KeyRound,
	Loader2,
	PackagePlus,
	SlidersHorizontal,
	Workflow,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
	captureSolutionEntities,
	getSolutionCaptureCandidates,
	previewSolutionCapture,
	type SolutionCaptureRequest,
	type SolutionEntitySummary,
	type SolutionConfigStatus,
} from "@/services/solutions";

type EntityKind =
	"workflows" | "apps" | "forms" | "agents" | "tables" | "claims";
type SelectableKind = EntityKind | "configs";

const SECTIONS: {
	key: SelectableKind;
	label: string;
	Icon: typeof Workflow;
}[] = [
	{ key: "workflows", label: "Workflows", Icon: Workflow },
	{ key: "apps", label: "Apps", Icon: AppWindow },
	{ key: "forms", label: "Forms", Icon: FileCode },
	{ key: "agents", label: "Agents", Icon: Bot },
	{ key: "tables", label: "Tables", Icon: Database },
	{ key: "claims", label: "Custom Claims", Icon: KeyRound },
	{ key: "configs", label: "Configs", Icon: SlidersHorizontal },
];

type Selection = Record<SelectableKind, Set<string>>;

function emptySelection(): Selection {
	return {
		workflows: new Set(),
		apps: new Set(),
		forms: new Set(),
		agents: new Set(),
		tables: new Set(),
		claims: new Set(),
		configs: new Set(),
	};
}

function toggleSelection(
	current: Selection,
	kind: SelectableKind,
	value: string,
): Selection {
	const next = { ...current, [kind]: new Set(current[kind]) };
	if (next[kind].has(value)) next[kind].delete(value);
	else next[kind].add(value);
	return next;
}

function replaceSelection(
	current: Selection,
	kind: SelectableKind,
	values: string[],
): Selection {
	return { ...current, [kind]: new Set(values) };
}

function itemValue(
	kind: SelectableKind,
	item: SolutionEntitySummary | SolutionConfigStatus,
): string {
	return kind === "configs"
		? (item as SolutionConfigStatus).key
		: (item as SolutionEntitySummary).id;
}

function itemName(
	kind: SelectableKind,
	item: SolutionEntitySummary | SolutionConfigStatus,
): string {
	return kind === "configs"
		? (item as SolutionConfigStatus).key
		: (item as SolutionEntitySummary).name;
}

function requestFromSelection(
	selection: Selection,
	includeImports: boolean,
): SolutionCaptureRequest {
	return {
		workflows: Array.from(selection.workflows),
		apps: Array.from(selection.apps),
		forms: Array.from(selection.forms),
		agents: Array.from(selection.agents),
		tables: Array.from(selection.tables),
		claims: Array.from(selection.claims),
		configs: Array.from(selection.configs),
		include_imports: includeImports,
	};
}

function selectedCount(selection: Selection): number {
	return Object.values(selection).reduce((sum, set) => sum + set.size, 0);
}

export function SolutionCaptureDialog({
	open,
	solutionId,
	onClose,
	onCaptured,
}: {
	open: boolean;
	solutionId: string;
	onClose: () => void;
	onCaptured: () => void;
}) {
	const busy = useRef(false);
	const errorRef = useRef<HTMLDivElement>(null);
	const returnFocus = useDialogReturnFocus();
	const [selection, setSelection] = useState<Selection>(() =>
		emptySelection(),
	);
	const [includeImports, setIncludeImports] = useState(false);
	const [captureError, setCaptureError] = useState<string | null>(null);

	useEffect(() => {
		if (captureError) {
			errorRef.current?.focus();
			errorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [captureError]);

	const { data, isLoading, error, refetch, isFetching } = useQuery({
		queryKey: ["solutions", solutionId, "capture-candidates"],
		queryFn: () => getSolutionCaptureCandidates(solutionId),
		enabled: open,
		retry: false,
	});

	const closeDialog = () => {
		setSelection(emptySelection());
		setIncludeImports(false);
		setCaptureError(null);
		onClose();
	};

	const totalSelected = useMemo(() => selectedCount(selection), [selection]);
	const hasCandidates = SECTIONS.some(
		({ key }) => (data?.[key]?.length ?? 0) > 0,
	);

	// Stable key for the preview query: sorted selected ids per kind + the
	// imports toggle. The preview is the deselectable guard (capture-design §3.3).
	const previewRequest = useMemo(
		() => ({
			workflows: Array.from(selection.workflows).sort(),
			apps: Array.from(selection.apps).sort(),
			forms: Array.from(selection.forms).sort(),
			agents: Array.from(selection.agents).sort(),
			tables: Array.from(selection.tables).sort(),
			claims: Array.from(selection.claims).sort(),
			configs: Array.from(selection.configs).sort(),
			include_imports: includeImports,
		}),
		[selection, includeImports],
	);

	const {
		data: preview,
		isFetching: previewLoading,
		error: previewError,
		refetch: retryPreview,
	} = useQuery({
		queryKey: ["solutions", solutionId, "capture-preview", previewRequest],
		queryFn: () => previewSolutionCapture(solutionId, previewRequest),
		enabled: open && totalSelected > 0,
		retry: false,
	});

	const capture = useMutation({
		onSettled: () => {
			busy.current = false;
		},
		mutationFn: () =>
			captureSolutionEntities(
				solutionId,
				requestFromSelection(selection, includeImports),
			),
		onSuccess: (result) => {
			setCaptureError(null);
			const count =
				result.workflows_captured +
				result.apps_captured +
				result.forms_captured +
				result.agents_captured +
				result.tables_captured +
				result.claims_captured +
				result.config_declarations_captured;
			toast.success(`Captured ${count} item${count === 1 ? "" : "s"}`);
			onCaptured();
			closeDialog();
		},
		onError: (err: unknown) => {
			const message =
				err instanceof Error
					? err.message
					: "Failed to capture entities";
			setCaptureError(message);
		},
	});

	function handleCapture() {
		if (
			busy.current ||
			capture.isPending ||
			totalSelected === 0 ||
			previewLoading
		)
			return;
		busy.current = true;
		setCaptureError(null);
		capture.mutate();
	}

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				if (!next && !capture.isPending) closeDialog();
			}}
		>
			<DialogContent
				{...returnFocus}
				className="[&>*]:min-w-0 [overflow-wrap:anywhere] w-[calc(100vw-1rem)] max-h-[92dvh] overflow-y-auto sm:max-w-4xl"
				showCloseButton={!capture.isPending}
				onEscapeKeyDown={(event) => {
					if (capture.isPending) event.preventDefault();
				}}
				onInteractOutside={(event) => {
					if (capture.isPending) event.preventDefault();
				}}
			>
				<DialogHeader>
					<DialogTitle>Capture existing entities</DialogTitle>
					<DialogDescription>
						Adopt loose same-scope entities into this Solution.
						Captured entities become Solution-managed.
					</DialogDescription>
				</DialogHeader>

				<fieldset
					disabled={capture.isPending}
					className="min-w-0 contents"
				>
					{isLoading ? (
						<div role="status" className="space-y-3 py-2">
							{[...Array(6)].map((_, i) => (
								<Skeleton
									key={i}
									className="h-16 w-full rounded-[var(--bf-radius-control)]"
								/>
							))}
						</div>
					) : error ? (
						<div
							role="alert"
							className="space-y-3 rounded-[var(--bf-radius-control)] border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
						>
							<p>
								{error instanceof Error
									? error.message
									: "Failed to load candidates"}
							</p>
							<Button
								variant="outline"
								className="min-h-11"
								disabled={isFetching}
								onClick={() => void refetch()}
							>
								{isFetching ? "Loading…" : "Retry candidates"}
							</Button>
						</div>
					) : !hasCandidates ? (
						<div className="rounded-[var(--bf-radius-control)] border border-dashed border-[color:var(--bf-info-soft)] px-4 py-10 text-center text-sm text-muted-foreground">
							No loose same-scope entities are available to
							capture.
						</div>
					) : (
						<div className="space-y-4">
							{SECTIONS.map(({ key, label, Icon }) => {
								const items = data?.[key] ?? [];
								if (items.length === 0) return null;
								const ids = items.map((item) =>
									itemValue(key, item),
								);
								const allSelected = ids.every((id) =>
									selection[key].has(id),
								);
								return (
									<section
										key={key}
										className="rounded-[var(--bf-radius-control)] border"
									>
										<div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
											<div className="flex min-w-0 items-center gap-2">
												<Icon className="h-4 w-4 text-muted-foreground" />
												<h3 className="truncate text-sm font-medium">
													{label}
												</h3>
												<Badge variant="secondary">
													{items.length}
												</Badge>
											</div>
											<label className="flex min-h-11 cursor-pointer items-center gap-2 rounded-[var(--bf-radius-control)] border border-transparent px-3 py-2 text-sm transition-colors motion-reduce:transition-none hover:bg-muted/50">
												<Checkbox
													checked={allSelected}
													aria-label={`Select all ${label}`}
													onCheckedChange={(
														checked,
													) => {
														setCaptureError(null);
														setSelection(
															(current) =>
																replaceSelection(
																	current,
																	key,
																	checked
																		? ids
																		: [],
																),
														);
													}}
												/>
												Select all
											</label>
										</div>
										<div className="divide-y">
											{items.map((item) => {
												const value = itemValue(
													key,
													item,
												);
												const name = itemName(
													key,
													item,
												);
												const description =
													item.description;
												return (
													<label
														key={value}
														className="flex min-h-11 cursor-pointer items-start gap-3 px-4 py-3 transition-colors motion-reduce:transition-none hover:bg-muted/50"
													>
														<Checkbox
															checked={selection[
																key
															].has(value)}
															aria-label={`Capture ${name}`}
															onCheckedChange={() => {
																setCaptureError(
																	null,
																);
																setSelection(
																	(current) =>
																		toggleSelection(
																			current,
																			key,
																			value,
																		),
																);
															}}
														/>
														<span className="min-w-0 flex-1">
															<span className="block [overflow-wrap:anywhere] font-mono text-sm font-medium">
																{name}
															</span>
															{description && (
																<span className="mt-0.5 block [overflow-wrap:anywhere] text-xs text-muted-foreground">
																	{
																		description
																	}
																</span>
															)}
														</span>
													</label>
												);
											})}
										</div>
									</section>
								);
							})}
						</div>
					)}

					{totalSelected > 0 && (
						<div className="space-y-3 border-t pt-4">
							<label className="flex min-h-11 cursor-pointer items-start gap-3 rounded-[var(--bf-radius-control)] border px-4 py-3 transition-colors motion-reduce:transition-none hover:bg-muted/50">
								<Checkbox
									checked={includeImports}
									aria-label="Include shared imports"
									onCheckedChange={(checked) => {
										setCaptureError(null);
										setIncludeImports(checked === true);
									}}
								/>
								<span className="min-w-0 flex-1">
									<span className="flex items-center gap-2 text-sm font-medium">
										<PackagePlus className="h-4 w-4 text-muted-foreground" />
										Include shared imports
									</span>
									<span className="mt-0.5 block text-xs text-muted-foreground">
										Bundle the <code>modules/</code> files
										the selected workflows import
										(transitively). Off by default — only
										the workflows&rsquo; own files are
										bundled.
									</span>
								</span>
							</label>

							<div className="rounded-[var(--bf-radius-control)] border">
								<div className="flex items-center gap-2 border-b px-4 py-2.5">
									<h3 className="text-sm font-medium">
										Dependency preview
									</h3>
									{previewLoading && (
										<Loader2 className="h-3.5 w-3.5 motion-safe:animate-spin text-muted-foreground" />
									)}
								</div>
								<div className="space-y-3 px-4 py-3 text-sm">
									{previewError ? (
										<div
											role="alert"
											className="space-y-2 text-destructive"
										>
											<p>
												Could not check dependencies for
												this selection.
											</p>
											<Button
												variant="outline"
												className="min-h-11"
												disabled={previewLoading}
												onClick={() =>
													void retryPreview()
												}
											>
												Retry dependencies
											</Button>
										</div>
									) : !preview && previewLoading ? (
										<p className="text-xs text-muted-foreground">
											Computing dependencies&hellip;
										</p>
									) : (preview?.pulled_in?.length ?? 0) ===
											0 &&
									  (preview?.outside_references?.length ??
											0) === 0 ? (
										<p className="text-xs text-muted-foreground">
											Nothing else is pulled in by this
											selection.
										</p>
									) : (
										<>
											{(preview?.pulled_in?.length ?? 0) >
												0 && (
												<div>
													<p className="mb-1 text-xs font-medium text-muted-foreground">
														Also pulled in
													</p>
													<ul className="space-y-1">
														{preview?.pulled_in?.map(
															(dep) => (
																<li
																	key={`${dep.kind}:${dep.ref}`}
																	className="flex items-center gap-2 font-mono text-xs"
																>
																	<Badge variant="secondary">
																		{
																			dep.kind
																		}
																	</Badge>
																	<span className="min-w-0 [overflow-wrap:anywhere]">
																		{
																			dep.name
																		}
																	</span>
																</li>
															),
														)}
													</ul>
												</div>
											)}
											{(preview?.outside_references
												?.length ?? 0) > 0 && (
												<div className="rounded-[var(--bf-radius-control)] border border-[color:var(--bf-warning-soft)] bg-[color:var(--bf-warning-soft)]/15 px-3 py-2">
													<p className="mb-1 flex items-center gap-1.5 text-xs font-medium text-[var(--bf-warning)]">
														<AlertTriangle className="h-3.5 w-3.5" />
														Outside references
													</p>
													<ul className="space-y-1 text-xs text-muted-foreground">
														{preview?.outside_references?.map(
															(ref, i) => (
																<li key={i}>
																	<span className="font-mono">
																		{
																			ref.target_name
																		}
																	</span>{" "}
																	is also used
																	by{" "}
																	{
																		ref.referencer_kind
																	}{" "}
																	<span className="font-mono">
																		{
																			ref.referencer_name
																		}
																	</span>
																	, which is
																	not being
																	captured.
																</li>
															),
														)}
													</ul>
												</div>
											)}
										</>
									)}
									{preview && (
										<p className="text-[11px] text-muted-foreground">
											Static scan — dynamic imports/refs
											are invisible. Add any missed file
											manually.
										</p>
									)}
								</div>
							</div>
						</div>
					)}
				</fieldset>
				{captureError ? (
					<Alert ref={errorRef} tabIndex={-1} variant="destructive">
						<AlertTitle>Could not capture entities</AlertTitle>
						<AlertDescription className="space-y-3">
							<p>{captureError}</p>
							<Button
								type="button"
								variant="outline"
								className="h-11"
								onClick={handleCapture}
								disabled={capture.isPending}
							>
								Retry capture
							</Button>
						</AlertDescription>
					</Alert>
				) : null}

				<DialogFooter>
					<Button
						type="button"
						variant="outline"
						className="min-h-11"
						disabled={capture.isPending}
						onClick={closeDialog}
					>
						Cancel
					</Button>
					<Button
						type="button"
						className="min-h-11"
						disabled={
							totalSelected === 0 ||
							capture.isPending ||
							previewLoading
						}
						onClick={handleCapture}
					>
						{(capture.isPending || previewLoading) && (
							<Loader2 className="mr-1.5 h-4 w-4 motion-safe:animate-spin" />
						)}
						Capture {totalSelected > 0 ? totalSelected : ""}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
