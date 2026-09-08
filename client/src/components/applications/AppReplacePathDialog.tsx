/**
 * AppReplacePathDialog
 *
 * Repoints an application's `repo_path` to a new source directory. Two-phase UI:
 *   pick     — folder picker + path text input + force toggle
 *   validated — inline validation results panel after the replace succeeds
 *
 * Mirrors the CLI `bifrost apps replace --repo-path` flag surface, including
 * `--force` which bypasses uniqueness / nesting / source-exists checks.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
	AlertTriangle,
	ArrowRightLeft,
	CheckCircle2,
	ChevronDown,
	ChevronRight,
	Folder,
	FolderOpen,
	Loader2,
	XCircle,
} from "lucide-react";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { workspaceOperations } from "@/components/file-tree/adapters/workspaceOperations";
import type { FileNode } from "@/components/file-tree";
import {
	useApplications,
	useReplaceApplication,
	useValidateApplication,
	type ApplicationPublic,
} from "@/hooks/useApplications";
import type { components } from "@/lib/v1";

type ValidationResponse = components["schemas"]["AppValidationResponse"];
type ValidationIssue = components["schemas"]["AppValidationIssue"];

interface AppReplacePathDialogProps {
	app: ApplicationPublic;
	open: boolean;
	onClose: () => void;
	onSuccess?: () => void;
}

type Phase = "pick" | "replacing" | "validated";

/** Single folder row in the picker tree. */
interface FolderRowProps {
	node: FileNode;
	level: number;
	selected: boolean;
	expanded: boolean;
	loading: boolean;
	onToggle: (path: string) => void;
	onSelect: (path: string) => void;
}

function FolderRow({
	node,
	level,
	selected,
	expanded,
	loading,
	onToggle,
	onSelect,
}: FolderRowProps) {
	return (
        <div className="flex min-w-0 items-start gap-1" style={{ paddingLeft: `${Math.min(level * 12, 72)}px` }}>
            <Button type="button" variant="ghost" size="icon-lg" aria-label={`${expanded ? "Collapse" : "Expand"} ${node.name}`} aria-expanded={expanded} onClick={() => onToggle(node.path)}>
                {loading ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </Button>
            <button type="button" aria-pressed={selected} onClick={() => onSelect(node.path)} onDoubleClick={() => onToggle(node.path)} className={cn("flex min-h-11 min-w-0 flex-1 items-center gap-2 rounded-[var(--bf-radius-control)] px-2 py-2 text-left text-sm transition-colors duration-[var(--bf-motion-feedback)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none", selected ? "bg-primary/10 text-primary" : "hover:bg-muted")}>
                {expanded ? <FolderOpen aria-hidden="true" className="h-4 w-4 shrink-0" /> : <Folder aria-hidden="true" className="h-4 w-4 shrink-0" />}
                <span className="min-w-0 font-mono text-xs [overflow-wrap:anywhere]">{node.name}</span>
            </button>
        </div>
    );
}

/**
 * Lightweight folder picker backed by `workspaceOperations.list`.
 *
 * Lazily loads directory contents on expand. File nodes are hidden — only
 * folders are rendered and selectable.
 */
function FolderPicker({
	selectedPath,
	onSelectPath,
}: {
	selectedPath: string;
	onSelectPath: (path: string) => void;
}) {
	const [childrenByPath, setChildrenByPath] = useState<
		Record<string, FileNode[]>
	>({});
	const [expanded, setExpanded] = useState<Set<string>>(new Set());
	const [loadingPaths, setLoadingPaths] = useState<Set<string>>(new Set());
	const [failedPaths, setFailedPaths] = useState<Set<string>>(new Set());
	const pendingPaths = useRef(new Set<string>());

	const loadPath = useCallback(async (path: string) => {
		if (pendingPaths.current.has(path)) return;
		pendingPaths.current.add(path);
		setFailedPaths(previous => { const next = new Set(previous); next.delete(path); return next; });
		setLoadingPaths((prev) => new Set(prev).add(path));
		try {
			const nodes = await workspaceOperations.list(path);
			setChildrenByPath((prev) => ({ ...prev, [path]: nodes }));
		} catch {
			setFailedPaths(previous => new Set(previous).add(path));
		} finally {
			pendingPaths.current.delete(path);
			setLoadingPaths((prev) => {
				const next = new Set(prev);
				next.delete(path);
				return next;
			});
		}
	}, []);

	// Load root on mount. setState inside loadPath only fires after the
	// awaited fetch resolves — wrapping in a void IIFE keeps the synchronous
	// effect body free of setState calls.
	useEffect(() => {
		void (async () => {
			await loadPath("");
		})();
	}, [loadPath]);

	const toggle = useCallback(
		(path: string) => {
			const isExpanded = expanded.has(path);
			if (isExpanded) {
				setExpanded((prev) => {
					const next = new Set(prev);
					next.delete(path);
					return next;
				});
				return;
			}
			setExpanded((prev) => new Set(prev).add(path));
			if (!childrenByPath[path]) {
				loadPath(path);
			}
		},
		[expanded, childrenByPath, loadPath],
	);

	// Auto-expand ancestors of the selectedPath when it changes (so the text
	// field → tree sync works). Only expand, never collapse. Adjust during
	// render with a previous-selectedPath sentinel rather than via
	// setState-in-effect.
	const [prevSelectedPath, setPrevSelectedPath] = useState(selectedPath);
	if (prevSelectedPath !== selectedPath && selectedPath) {
		setPrevSelectedPath(selectedPath);
		const parts = selectedPath.split("/");
		const ancestors: string[] = [];
		for (let i = 1; i < parts.length; i++) {
			ancestors.push(parts.slice(0, i).join("/"));
		}
		setExpanded((prev) => {
			let changed = false;
			const next = new Set(prev);
			for (const a of ancestors) {
				if (!next.has(a)) {
					next.add(a);
					changed = true;
				}
			}
			return changed ? next : prev;
		});
	}

    // Directory requests run after render; failed branches wait for explicit retry.
    useEffect(() => {
        void (async () => {
            for (const path of expanded) {
                if (!childrenByPath[path] && !failedPaths.has(path)) await loadPath(path);
            }
        })();
    }, [expanded, childrenByPath, failedPaths, loadPath]);

	const renderLevel = (parentPath: string, level: number): React.ReactNode => {
		if (failedPaths.has(parentPath)) return <div role="alert" className="space-y-2 p-2 text-sm"><p className="text-destructive">Couldn't load {parentPath || "workspace folders"}.</p><Button type="button" variant="outline" className="min-h-11" onClick={() => void loadPath(parentPath)}>Retry folders</Button></div>;
		const nodes = childrenByPath[parentPath];
		if (!nodes) return null;
		const folders = nodes.filter((n) => n.type === "folder");
		return folders.map((node) => (
			<div key={node.path}>
				<FolderRow
					node={node}
					level={level}
					selected={selectedPath === node.path}
					expanded={expanded.has(node.path)}
					loading={loadingPaths.has(node.path)}
					onToggle={toggle}
					onSelect={onSelectPath}
				/>
				{expanded.has(node.path) && renderLevel(node.path, level + 1)}
			</div>
		));
	};

	const rootLoading = loadingPaths.has("") && !childrenByPath[""];

	return (
		<div className="rounded-[var(--bf-radius-surface)] border max-h-64 overflow-auto p-1 bg-muted/50">
			{rootLoading ? (
				<div role="status" className="flex items-center justify-center py-4 text-sm text-muted-foreground">
					<Loader2 aria-hidden="true" className="h-4 w-4 animate-spin mr-2 motion-reduce:animate-none" />
					Loading workspace…
				</div>
			) : (
				renderLevel("", 0)
			)}
		</div>
	);
}

interface ValidationSection {
	title: string;
	issues: ValidationIssue[];
	variant: "error" | "warning";
}

function ValidationResultsPanel({
	result,
}: {
	result: ValidationResponse | null;
}) {
	if (!result) return null;

	if (result.valid && result.warnings.length === 0) {
		return (
			<div className="flex items-center gap-2 p-3 rounded-[var(--bf-radius-surface)] bg-[var(--bf-success)]/10 text-[var(--bf-success)] text-sm">
				<CheckCircle2 className="h-4 w-4 shrink-0" />
				<span>No issues found. Your app source looks good.</span>
			</div>
		);
	}

	const sections: ValidationSection[] = [];
	if (result.errors.length > 0) {
		sections.push({
			title: `Errors (${result.errors.length})`,
			issues: result.errors,
			variant: "error",
		});
	}
	if (result.warnings.length > 0) {
		sections.push({
			title: `Warnings (${result.warnings.length})`,
			issues: result.warnings,
			variant: "warning",
		});
	}

	return (
		<div className="space-y-3">
			{sections.map((section) => (
				<div key={section.title} className="overflow-hidden rounded-[var(--bf-radius-surface)] border">
					<h3
						className={cn(
							"px-3 py-2 text-sm font-medium border-b flex items-center gap-2",
							section.variant === "error"
								? "bg-destructive/10 text-destructive"
								: "bg-[var(--bf-warning)]/10 text-[var(--bf-warning)]",
						)}
					>
						{section.variant === "error" ? (
							<XCircle className="h-4 w-4" />
						) : (
							<AlertTriangle className="h-4 w-4" />
						)}
						{section.title}
					</h3>
					<ul aria-label={section.title} className="divide-y text-sm">
						{section.issues.map((issue, idx) => (
							<li key={idx} className="px-3 py-2">
								<div className="flex flex-col items-start gap-2 sm:flex-row">
									<Badge variant="outline" className="text-xs shrink-0">
										{issue.severity}
									</Badge>
									<div className="min-w-0 flex-1">
										<div className="font-mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
											{issue.file}
											{issue.line != null && `:${issue.line}`}
										</div>
										<div className="mt-1 text-sm [overflow-wrap:anywhere]">{issue.message}</div>
									</div>
								</div>
							</li>
						))}
					</ul>
				</div>
			))}
		</div>
	);
}

function AppReplacePathDialogBody({
	app,
	onClose,
	onSuccess,
}: {
	app: ApplicationPublic;
	onClose: () => void;
	onSuccess?: () => void;
}) {
	const navigate = useNavigate();
	const replaceApp = useReplaceApplication({ toastNotifications: false });
	const validateApp = useValidateApplication();
	const { data: appList } = useApplications();

	const [phase, setPhase] = useState<Phase>("pick");
	const [replaceError, setReplaceError] = useState(false);
	const [targetPath, setTargetPathState] = useState("");
	const [force, setForce] = useState(false);
	const [advancedOpen, setAdvancedOpen] = useState(false);
	const [targetHasFiles, setTargetHasFiles] = useState<boolean | null>(null);
	const [targetChecking, setTargetChecking] = useState(false);
	const [targetCheckError, setTargetCheckError] = useState(false);
	const validationBusy = useRef(false);
	const replacingRef = useRef(false);
	const [validating, setValidating] = useState(false);
	const [validationError, setValidationError] = useState(false);
	const [validationResult, setValidationResult] =
		useState<ValidationResponse | null>(null);

	// Probing state for the source-exists check. We run it from the setter
	// rather than an effect so we can satisfy react-hooks/set-state-in-effect.
	const probeTokenRef = useRef(0);

	const setTargetPath = useCallback((next: string) => {
		setTargetPathState(next);
		setTargetCheckError(false);
		setTargetHasFiles(null);
		const token = ++probeTokenRef.current;
		if (!next) {
			setTargetHasFiles(null);
			setTargetChecking(false);
			return;
		}
		setTargetChecking(true);
		workspaceOperations
			.list(next)
			.then((nodes) => {
				if (probeTokenRef.current !== token) return;
				setTargetHasFiles(nodes.some((n) => n.type === "file"));
			})
			.catch(() => {
				if (probeTokenRef.current !== token) return;
				setTargetCheckError(true);
			})
			.finally(() => {
				if (probeTokenRef.current !== token) return;
				setTargetChecking(false);
			});
	}, []);

	// Client-side pre-flight warnings so the user sees feedback before submitting.
	const warnings = useMemo(() => {
		const out: { kind: "uniqueness" | "nesting" | "empty"; message: string }[] =
			[];
		if (!targetPath) return out;
		const normalized = targetPath.replace(/\/$/, "");
		if (normalized === app.repo_path) {
			return out;
		}
		const others = (appList?.applications ?? []).filter((a) => a.id !== app.id);
		const exactMatch = others.find((a) => a.repo_path === normalized);
		if (exactMatch) {
			out.push({
				kind: "uniqueness",
				message: `Path is already claimed by "${exactMatch.name}".`,
			});
		}
		for (const other of others) {
			if (!other.repo_path) continue;
			if (normalized.startsWith(`${other.repo_path}/`)) {
				out.push({
					kind: "nesting",
					message: `Path is nested under "${other.name}" (${other.repo_path}).`,
				});
				break;
			}
			if (other.repo_path.startsWith(`${normalized}/`)) {
				out.push({
					kind: "nesting",
					message: `Path would contain "${other.name}" (${other.repo_path}) nested inside it.`,
				});
				break;
			}
		}
		if (targetHasFiles === false && !targetChecking) {
			out.push({
				kind: "empty",
				message:
					"No source files found at this path. Enable Force if you plan to push files next.",
			});
		}
		return out;
	}, [targetPath, app, appList, targetHasFiles, targetChecking]);

	const hasBlockingWarning = warnings.length > 0;
	const canReplace =
		!!targetPath &&
		targetPath !== app.repo_path &&
		!targetChecking &&
		(!targetCheckError || force) &&
		(!hasBlockingWarning || force);

	const runValidation = async () => {
        if (validationBusy.current) return;
        validationBusy.current = true;
        setValidating(true);
        setValidationError(false);
        try {
            const result = await validateApp.mutateAsync({ params: { path: { app_id: app.id } } });
            setValidationResult(result);
        } catch {
            setValidationResult(null);
            setValidationError(true);
        } finally {
            validationBusy.current = false;
            setValidating(false);
        }
    };

	const handleReplace = async () => {
        if (replacingRef.current || !canReplace) return;
        replacingRef.current = true;
        setReplaceError(false);
        setPhase("replacing");
        try {
            await replaceApp.mutateAsync({
                params: { path: { app_id: app.id } },
                body: { repo_path: targetPath, force },
            });
        } catch {
            setReplaceError(true);
            setPhase("pick");
            return;
        } finally {
            replacingRef.current = false;
        }
        setPhase("validated");
        onSuccess?.();
        await runValidation();
    };

    const handleClose = () => { if (!replacingRef.current) onClose(); };

	return (
		<Dialog open onOpenChange={(next) => { if (!next) handleClose(); }}>
		<DialogContent className="flex max-h-[90dvh] flex-col gap-0 overflow-hidden p-0 sm:max-w-xl">
			<DialogHeader className="shrink-0 border-b p-4 pr-16!">
				<DialogTitle className="flex items-center gap-2">
					<ArrowRightLeft className="h-5 w-5" />
					Replace app path
				</DialogTitle>
				<DialogDescription>
					Repoint <span className="font-medium">{app.name}</span> to a
					different source directory. Current path:{" "}
					<code className="bg-muted px-1 py-0.5 rounded text-xs">
						{phase === "validated" ? targetPath : app.repo_path}
					</code>
				</DialogDescription>
			</DialogHeader>

			{phase === "validated" ? (
					<div className="flex min-h-0 flex-1 flex-col overflow-hidden"><div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
						<div className="flex flex-wrap items-center gap-2 p-3 rounded-[var(--bf-radius-surface)] bg-muted text-sm">
							<CheckCircle2 className="h-4 w-4 shrink-0 text-[var(--bf-success)]" />
							Path replaced. Now pointing to{" "}
							<code className="min-w-0 bg-background px-1 py-0.5 rounded-[var(--bf-radius-control)] text-xs [overflow-wrap:anywhere]">
								{targetPath}
							</code>
						</div>
						{validating && <p role="status" className="text-sm text-muted-foreground">Validating source files…</p>}
                        {validationError && <div role="alert" className="space-y-3 text-sm"><p className="text-destructive">The path was replaced, but source validation failed to run.</p><Button type="button" variant="outline" className="min-h-11" onClick={() => void runValidation()}>Retry validation</Button></div>}
                        <ValidationResultsPanel result={validationResult} />
						</div><DialogFooter className="grid shrink-0 grid-cols-2 border-t p-4 sm:flex [&_button]:min-h-11">
							<Button variant="outline" onClick={handleClose}>
								Close
							</Button>
							<Button
								onClick={() => {
									navigate(`/apps/${app.slug}/edit`);
									handleClose();
								}}
							>
								Open app
							</Button>
						</DialogFooter>
					</div>
				) : (
					<div className="flex min-h-0 flex-1 flex-col overflow-hidden"><div inert={phase === "replacing"} className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
						<div className="space-y-2">
							<label
								htmlFor="target-path"
								className="text-sm font-medium"
							>
								New path
							</label>
							<Input
								id="target-path"
								value={targetPath}
								onChange={(e) => setTargetPath(e.target.value)}
								placeholder="apps/my-app-v2"
								className="min-h-11 font-mono text-sm"
								disabled={phase === "replacing"}
							/>
							<FolderPicker
								selectedPath={targetPath}
								onSelectPath={setTargetPath}
							/>
						</div>

						{replaceError && <p role="alert" className="text-sm text-destructive">Couldn't replace the path. Your selection is ready to retry.</p>}

						{targetChecking && <p role="status" className="text-sm text-muted-foreground">Checking source files…</p>}
						{targetCheckError && <div role="alert" className="space-y-2 text-sm"><p className="text-destructive">Couldn't check this path. Retry the check, or use Force to skip it.</p><Button type="button" variant="outline" className="min-h-11" onClick={() => setTargetPath(targetPath)}>Retry path check</Button></div>}
						{warnings.length > 0 && (
							<div className="space-y-2">
								{warnings.map((w) => (
									<div
										key={w.kind}
										className={cn(
											"flex items-start gap-2 p-3 rounded-[var(--bf-radius-surface)] text-sm",
											w.kind === "empty"
												? "bg-[var(--bf-warning)]/10 text-[var(--bf-warning)]"
												: "bg-destructive/10 text-destructive",
										)}
									>
										<AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
										<span className="min-w-0 [overflow-wrap:anywhere]">{w.message}</span>
									</div>
								))}
							</div>
						)}

						<Collapsible
							open={advancedOpen}
							onOpenChange={setAdvancedOpen}
						>
							<CollapsibleTrigger asChild>
								<button
									type="button"
									className="flex min-h-11 items-center gap-2 text-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
								>
									{advancedOpen ? (
										<ChevronDown className="h-3 w-3" />
									) : (
										<ChevronRight className="h-3 w-3" />
									)}
									Advanced
								</button>
							</CollapsibleTrigger>
							<CollapsibleContent className="pt-3">
								<label className="flex min-h-11 items-start gap-2 text-sm">
									<Checkbox
										checked={force}
										onCheckedChange={(v) => setForce(v === true)}
										disabled={phase === "replacing"}
										className="mt-0.5"
									/>
									<span>
										<span className="font-medium">
											Force (skip validation)
										</span>
										<span className="block text-xs text-muted-foreground">
											Bypass uniqueness, nesting, and source-exists
											checks. Matches the CLI's{" "}
											<code className="bg-muted px-1 rounded">
												--force
											</code>{" "}
											flag — use when repointing before files are
											pushed.
										</span>
									</span>
								</label>
							</CollapsibleContent>
						</Collapsible>

						</div>{phase === "replacing" && <p role="status" className="sr-only">Replacing path…</p>}<DialogFooter className="grid shrink-0 grid-cols-2 border-t p-4 sm:flex [&_button]:min-h-11">
							<Button
								variant="outline"
								onClick={handleClose}
								disabled={phase === "replacing"}
							>
								Cancel
							</Button>
							<Button
								onClick={handleReplace}
								disabled={!canReplace || phase === "replacing"}
							>
								{phase === "replacing" ? (
									<>
										<Loader2 aria-hidden="true" className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
										Replacing…
									</>
								) : (
									<>
										<ArrowRightLeft className="mr-2 h-4 w-4" />
										<span className="min-w-0 whitespace-normal">{replaceError ? "Retry replace" : "Replace"}</span>
									</>
								)}
							</Button>
						</DialogFooter>
					</div>
				)}
		</DialogContent>
		</Dialog>
	);
}

/**
 * Thin outer component. Mounts the body only when `open` is true so state
 * resets every time the dialog is opened — avoids having to do setState
 * inside a useEffect.
 */
export function AppReplacePathDialog({ app, open, onClose, onSuccess }: AppReplacePathDialogProps) {
    return open ? <AppReplacePathDialogBody app={app} onClose={onClose} onSuccess={onSuccess} /> : null;
}

export default AppReplacePathDialog;
