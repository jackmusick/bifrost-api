import {
	PageWorkspace,
	PageScrollArea,
} from "@/components/layout/PageWorkspace";
import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Search } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ArtifactRecord } from "./ArtifactRecord";
import { ArtifactDeleteDialog, ArtifactRenameDialog } from "./ArtifactDialogs";
import { FilePreviewSheet } from "./FilePreviewSheet";
import {
	deleteChatArtifact,
	listChatArtifacts,
	renameChatArtifact,
	type ChatArtifactPublic,
} from "@/services/chatAttachments";

type LibraryFilter = "all" | "artifact" | "attachment";

export function ArtifactsLibrary() {
	const queryClient = useQueryClient();
	const headingRef = useRef<HTMLHeadingElement>(null);
	const renameTriggerRef = useRef<HTMLButtonElement | null>(null);
	const deleteTriggerRef = useRef<HTMLButtonElement | null>(null);
	const renameBusyRef = useRef(false);
	const deleteBusyRef = useRef(false);

	const [search, setSearch] = useState("");
	const [filter, setFilter] = useState<LibraryFilter>("all");
	const [preview, setPreview] = useState<ChatArtifactPublic | null>(null);
	const [renameTarget, setRenameTarget] = useState<ChatArtifactPublic | null>(
		null,
	);
	const [deleteTarget, setDeleteTarget] = useState<ChatArtifactPublic | null>(
		null,
	);
	const [filename, setFilename] = useState("");
	const [isRenaming, setIsRenaming] = useState(false);
	const [isDeleting, setIsDeleting] = useState(false);
	const [renameError, setRenameError] = useState<string | null>(null);
	const [deleteError, setDeleteError] = useState<string | null>(null);
	const [deletePreferFallback, setDeletePreferFallback] = useState(false);

	const artifactsQuery = useQuery({
		queryKey: ["chat-artifacts"],
		queryFn: listChatArtifacts,
	});

	const renameMutation = useMutation({
		mutationFn: ({ id, name }: { id: string; name: string }) =>
			renameChatArtifact(id, name),
	});

	const deleteMutation = useMutation({
		mutationFn: deleteChatArtifact,
	});

	const filtered = useMemo(() => {
		const term = search.trim().toLocaleLowerCase();
		return (artifactsQuery.data ?? []).filter((artifact) => {
			if (filter !== "all" && artifact.kind !== filter) return false;
			if (!term) return true;
			return [artifact.filename, artifact.conversation_title]
				.filter(Boolean)
				.some((value) => value!.toLocaleLowerCase().includes(term));
		});
	}, [artifactsQuery.data, filter, search]);

	const startRename = (
		artifact: ChatArtifactPublic,
		trigger: HTMLButtonElement,
	) => {
		renameTriggerRef.current = trigger;
		renameBusyRef.current = false;
		setIsRenaming(false);
		setRenameError(null);
		setRenameTarget(artifact);
		setFilename(artifact.filename);
	};

	const startDelete = (
		artifact: ChatArtifactPublic,
		trigger: HTMLButtonElement,
	) => {
		deleteTriggerRef.current = trigger;
		deleteBusyRef.current = false;
		setIsDeleting(false);
		setDeleteError(null);
		setDeletePreferFallback(false);
		setDeleteTarget(artifact);
	};

	const handleRenameSubmit = async () => {
		if (!renameTarget?.id || renameBusyRef.current || !filename.trim())
			return;

		const renameId = renameTarget.id;
		const nextFilename = filename.trim();
		renameBusyRef.current = true;
		setIsRenaming(true);
		setRenameError(null);

		try {
			const renamed = await renameMutation.mutateAsync({
				id: renameId,
				name: nextFilename,
			});

			queryClient.setQueryData<ChatArtifactPublic[]>(
				["chat-artifacts"],
				(current = []) =>
					current.map((item) =>
						item.id === renamed.id ? renamed : item,
					),
			);
			setRenameTarget(null);
			toast.success("Artifact renamed");
		} catch (error) {
			setRenameError(
				error instanceof Error
					? error.message
					: "Could not rename this artifact. Try again.",
			);
		} finally {
			renameBusyRef.current = false;
			setIsRenaming(false);
		}
	};

	const handleDeleteConfirm = async () => {
		if (!deleteTarget?.id || deleteBusyRef.current) return;

		const deleteId = deleteTarget.id;
		deleteBusyRef.current = true;
		setIsDeleting(true);
		setDeleteError(null);

		try {
			await deleteMutation.mutateAsync(deleteId);
			queryClient.setQueryData<ChatArtifactPublic[]>(
				["chat-artifacts"],
				(current = []) =>
					current.filter((item) => item.id !== deleteId),
			);
			setDeletePreferFallback(true);
			setDeleteTarget(null);
			toast.success("Artifact deleted");
		} catch (error) {
			setDeleteError(
				error instanceof Error
					? error.message
					: "Could not delete this artifact. Try again.",
			);
		} finally {
			deleteBusyRef.current = false;
			setIsDeleting(false);
		}
	};

	return (
		<div className="min-h-0 flex-1 overflow-y-auto lg:overflow-hidden">
			<PageWorkspace className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-8 sm:py-8">
				<div className="shrink-0 space-y-6">
					<div className="shrink-0">
						<h1
							ref={headingRef}
							tabIndex={-1}
							className="font-display text-2xl font-semibold tracking-tight outline-none"
						>
							Artifacts
						</h1>
						<p className="mt-1 text-sm text-muted-foreground">
							Files created or used in your conversations.
						</p>
					</div>

					<div className="flex flex-wrap items-center justify-between gap-3">
						<div
							className="flex shrink-0 flex-wrap gap-1"
							role="group"
							aria-label="Artifact type"
						>
							{(["all", "artifact", "attachment"] as const).map(
								(value) => (
									<Button
										key={value}
										type="button"
										variant={
											filter === value
												? "secondary"
												: "ghost"
										}
										size="sm"
										aria-pressed={filter === value}
										onClick={() => setFilter(value)}
										className="min-h-11 capitalize"
									>
										{value === "artifact"
											? "Generated"
											: value === "attachment"
												? "Uploaded"
												: value}
									</Button>
								),
							)}
						</div>

						<label className="relative block w-full sm:w-72">
							<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
							<span className="sr-only">Search artifacts</span>
							<Input
								value={search}
								onChange={(event) =>
									setSearch(event.target.value)
								}
								placeholder="Search files"
								className="h-11 pl-9"
							/>
						</label>
					</div>
				</div>

				<PageScrollArea className="space-y-6">
					{artifactsQuery.isError && (
						<div
							role="alert"
							className="mb-4 flex flex-col items-start gap-3 rounded-[var(--bf-radius-control)] border border-[var(--bf-warning)]/20 bg-[var(--bf-warning-soft)] p-4 text-sm sm:flex-row sm:items-center sm:justify-between"
						>
							<p>
								{artifactsQuery.data
									? "Could not refresh artifacts. Previously loaded files are still shown."
									: "Artifacts could not be loaded. Retry to continue."}
							</p>
							<Button
								type="button"
								variant="outline"
								className="min-h-11 shrink-0"
								disabled={artifactsQuery.isFetching}
								onClick={() => {
									void artifactsQuery.refetch();
								}}
							>
								{artifactsQuery.isFetching
									? "Retrying…"
									: "Retry artifacts"}
							</Button>
						</div>
					)}

					<div className="overflow-hidden rounded-[var(--bf-radius-surface)] border bg-background">
						{artifactsQuery.isLoading ? (
							<div
								role="status"
								aria-label="Loading artifacts"
								className="space-y-1 p-2"
							>
								{[1, 2, 3, 4].map((item) => (
									<Skeleton
										key={item}
										className="h-16 w-full"
									/>
								))}
							</div>
						) : artifactsQuery.isError &&
						  !artifactsQuery.data ? null : filtered.length ===
						  0 ? (
							<div className="p-10 text-center">
								<FileText className="mx-auto h-7 w-7 text-muted-foreground" />
								<p className="mt-3 text-sm font-medium">
									{search.trim() || filter !== "all"
										? "No matching files"
										: "No artifacts yet"}
								</p>
								<p className="mt-1 text-sm text-muted-foreground">
									{search.trim() || filter !== "all"
										? "Try another search or show all file types."
										: "Generated files and chat attachments will appear here."}
								</p>
								{(search.trim() || filter !== "all") && (
									<Button
										type="button"
										variant="outline"
										className="mt-4 min-h-11"
										onClick={() => {
											setSearch("");
											setFilter("all");
										}}
									>
										Clear filters
									</Button>
								)}
							</div>
						) : (
							<ul className="divide-y">
								{filtered.map((artifact) => (
									<ArtifactRecord
										key={artifact.id}
										artifact={artifact}
										onPreview={setPreview}
										onRename={startRename}
										onDelete={startDelete}
									/>
								))}
							</ul>
						)}
					</div>
				</PageScrollArea>
			</PageWorkspace>

			<FilePreviewSheet
				conversationId={preview?.conversation_id ?? ""}
				attachment={preview}
				attachments={filtered}
				onAttachmentChange={(attachment) =>
					setPreview(attachment as ChatArtifactPublic)
				}
				onOpenChange={(open) => !open && setPreview(null)}
			/>

			<ArtifactRenameDialog
				open={renameTarget !== null}
				filename={filename}
				pending={isRenaming}
				error={renameError}
				onOpenChange={(open) => {
					if (!open) {
						setRenameTarget(null);
						setRenameError(null);
					}
				}}
				onFilenameChange={setFilename}
				onSubmit={() => {
					void handleRenameSubmit();
				}}
				returnFocusRef={renameTriggerRef}
			/>

			<ArtifactDeleteDialog
				open={deleteTarget !== null}
				target={deleteTarget}
				pending={isDeleting}
				error={deleteError}
				preferFallback={deletePreferFallback}
				fallbackRef={headingRef}
				onOpenChange={(open) => {
					if (!open) {
						setDeleteTarget(null);
						setDeleteError(null);
					}
				}}
				onConfirm={() => {
					void handleDeleteConfirm();
				}}
				returnFocusRef={deleteTriggerRef}
			/>
		</div>
	);
}
