import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Search } from "lucide-react";
import { $api } from "@/lib/api-client";
import { getErrorMessage } from "@/lib/api-error";
import { useAuth } from "@/contexts/AuthContext";
import { useCreateConversation, useConversations } from "@/hooks/useChat";
import {
	PageWorkspace,
	PageScrollArea,
} from "@/components/layout/PageWorkspace";
import { ListPageHeader } from "@/components/layout/ListPageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { PageLoader } from "@/components/PageLoader";
import { toast } from "sonner";
import type {
	HomeCollection,
	HomeCollectionWrite,
	HomeResource,
} from "@/services/home";
import { ResourceCard } from "./Home/components/ResourceCard";
import { HomeBrowse } from "./Home/components/HomeBrowse";
import { CollectionStrip } from "./Home/components/CollectionStrip";
import { RecentWork } from "./Home/components/RecentWork";
import { CollectionEditor } from "./Home/components/CollectionEditor";

const NO_RESOURCES: HomeResource[] = [];

/** Home launches work using existing resource grants. Collections organize; they never authorize. */
export function Home() {
	const { isPlatformAdmin } = useAuth();
	const navigate = useNavigate();
	const [params, setParams] = useSearchParams();
	const queryClient = useQueryClient();
	const home = $api.useQuery("get", "/api/home");
	const conversations = useConversations();
	const createConversation = useCreateConversation();
	const [editor, setEditor] = useState<HomeCollection | "new" | null>(null);
	const [editorError, setEditorError] = useState("");
	const [opening, setOpening] = useState(false);
	const refresh = () =>
		queryClient.invalidateQueries({ queryKey: ["get", "/api/home"] });
	const preference = $api.useMutation(
		"put",
		"/api/home/preferences/{resource_key}",
		{ onSuccess: refresh },
	);
	const create = $api.useMutation("post", "/api/home/collections");
	const update = $api.useMutation(
		"put",
		"/api/home/collections/{collection_id}",
	);
	const remove = $api.useMutation(
		"delete",
		"/api/home/collections/{collection_id}",
	);
	const busy = create.isPending || update.isPending || remove.isPending;
	const resources = home.data?.resources ?? NO_RESOURCES;
	const collections = home.data?.collections ?? [];
	const selected = collections.find(
		(collection) => collection.id === params.get("collection"),
	);
	const search = params.get("q") ?? "";
	const kind = params.get("type") ?? "all";
	const org = params.get("org") ?? "all";
	const grid = params.get("view") === "grid";
	const updateParam = (key: string, value: string | null) =>
		setParams(
			(previous) => {
				const next = new URLSearchParams(previous);
				if (value) next.set(key, value);
				else next.delete(key);
				next.delete("page");
				if (key === "org") next.delete("collection");
				return next;
			},
			{ replace: true },
		);
	const orgOptions = useMemo(
		() =>
			[
				...new Map(
					resources
						.filter((resource) => resource.organization_id)
						.map((resource) => [
							resource.organization_id!,
							resource.organization_name,
						]),
				).entries(),
			].sort((a, b) => a[1].localeCompare(b[1])),
		[resources],
	);
	const inScope = (resource: HomeResource) =>
		org === "all" ||
		(org === "global"
			? !resource.organization_id
			: resource.organization_id === org || !resource.organization_id);
	const pinned = resources.filter(
		(resource) => resource.pinned && inScope(resource),
	);
	const recent = resources
		.filter((resource) => resource.last_opened_at && inScope(resource))
		.sort(
			(a, b) =>
				Date.parse(b.last_opened_at!) - Date.parse(a.last_opened_at!),
		)
		.slice(0, 3);
	const ordered = selected
		? (selected.resource_keys ?? []).flatMap(
				(key) =>
					resources.find((resource) => resource.key === key) ?? [],
			)
		: resources;
	const filtered = ordered.filter(
		(resource) =>
			inScope(resource) &&
			(kind === "all" || resource.kind === kind) &&
			`${resource.name} ${resource.description ?? ""} ${resource.organization_name}`
				.toLowerCase()
				.includes(search.toLowerCase()),
	);
	const requestedPage = Math.max(0, Number(params.get("page")) || 0);
	const page = Math.min(
		Math.floor(requestedPage),
		Math.max(0, Math.ceil(filtered.length / 12) - 1),
	);
	const visible = filtered.slice(page * 12, (page + 1) * 12);
	const openResource = async (resource: HomeResource) => {
		if (opening) return;
		setOpening(true);
		try {
			let href = resource.href;
			if (resource.kind === "agent") {
				const conversation = await createConversation.mutateAsync({
					body: { agent_id: resource.id, channel: "chat" },
				});
				href = `/chat/${conversation.id}`;
			}
			try {
				await preference.mutateAsync({
					params: { path: { resource_key: resource.key } },
					body: { opened: true },
				});
			} catch {
				toast.error("Could not save this item to recent work");
			}
			navigate(href);
		} catch {
			/* Conversation mutation reports the actionable API error. */
		} finally {
			setOpening(false);
		}
	};
	const pinResource = async (resource: HomeResource) => {
		try {
			await preference.mutateAsync({
				params: { path: { resource_key: resource.key } },
				body: { pinned: !resource.pinned, opened: false },
			});
		} catch (error) {
			toast.error(getErrorMessage(error, "Could not save favorite"));
		}
	};
	const openEditor = (collection: HomeCollection | "new") => {
		setEditorError("");
		setEditor(collection);
	};
	const saveCollection = async (data: HomeCollectionWrite) => {
		setEditorError("");
		try {
			const result =
				editor && editor !== "new"
					? await update.mutateAsync({
							params: { path: { collection_id: editor.id } },
							body: data,
						})
					: await create.mutateAsync({ body: data });
			await refresh();
			setEditor(null);
			updateParam("collection", result.id);
			toast.success("Collection saved");
		} catch (error) {
			setEditorError(getErrorMessage(error, "Could not save collection"));
		}
	};
	const deleteCollection = async () => {
		if (!editor || editor === "new") return;
		try {
			await remove.mutateAsync({
				params: { path: { collection_id: editor.id } },
			});
			await refresh();
			setEditor(null);
			if (selected?.id === editor.id) updateParam("collection", null);
		} catch (error) {
			setEditorError(
				getErrorMessage(error, "Could not delete collection"),
			);
		}
	};
	if (home.isLoading) return <PageLoader message="Loading your workspace…" />;
	if (home.isError)
		return (
			<div className="space-y-4">
				<h1 className="font-display text-2xl">Home could not load</h1>
				<p role="alert" className="text-muted-foreground">
					Your resources and collections could not be retrieved.
				</p>
				<Button
					onClick={() => void home.refetch()}
					disabled={home.isFetching}
				>
					Try again
				</Button>
			</div>
		);
	return (
		<PageWorkspace className="gap-5">
			<div className="shrink-0 space-y-4">
				<ListPageHeader
					title="Home"
					description="Your apps, forms, and conversations."
					actions={
						<Button variant="outline" asChild>
							<Link to="/chat">
								<MessageSquare className="size-4" />
								New chat
							</Link>
						</Button>
					}
				/>
				<div className="flex flex-col gap-3 sm:flex-row">
					<div className="relative min-w-0 flex-1">
						<Search className="pointer-events-none absolute left-3 top-3 size-4 text-muted-foreground" />
						<Input
							className="h-10 pl-9"
							aria-label="Search Home resources"
							placeholder="Search apps, forms, and agents…"
							value={search}
							onChange={(event) =>
								updateParam("q", event.target.value)
							}
						/>
					</div>
					{isPlatformAdmin && (
						<Select
							value={org}
							onValueChange={(value) => updateParam("org", value)}
						>
							<SelectTrigger
								aria-label="Organization filter"
								className="h-10 w-full sm:w-60"
							>
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="all">
									All organizations
								</SelectItem>
								<SelectItem value="global">
									Global resources
								</SelectItem>
								{orgOptions.map(([id, name]) => (
									<SelectItem key={id} value={id}>
										{name}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					)}
				</div>
			</div>
			<PageScrollArea
				aria-label="Home workspace"
				className="space-y-7 pb-2 pr-1"
			>
				{!search && (
					<>
						<section
							className="space-y-3"
							aria-label="Pinned resources"
						>
							<div className="flex items-baseline gap-3">
								<h2 className="text-base font-semibold">
									Pinned
								</h2>
								<span className="text-xs text-muted-foreground">
									Personal favorites
								</span>
							</div>
							{pinned.length ? (
								<div className="grid gap-3 sm:grid-cols-[repeat(auto-fit,minmax(14rem,1fr))]">
									{pinned.map((resource) => (
										<ResourceCard
											key={resource.key}
											resource={resource}
											onOpen={openResource}
											onPin={pinResource}
											busy={
												opening || preference.isPending
											}
										/>
									))}
								</div>
							) : (
								<p className="py-1 text-sm text-muted-foreground">
									Star a resource below to keep it close at
									hand.
								</p>
							)}
						</section>
						<CollectionStrip
							collections={collections.filter(
								(collection) =>
									org === "all" ||
									!collection.shared ||
									!collection.organization_id ||
									collection.organization_id === org,
							)}
							selected={selected?.id ?? null}
							onSelect={(id) => updateParam("collection", id)}
							onEdit={openEditor}
							onCreate={() => openEditor("new")}
						/>
						<RecentWork
							recent={recent}
							conversations={conversations.data}
							showConversations={org === "all"}
							onOpen={openResource}
							busy={opening}
						/>
					</>
				)}
				<HomeBrowse
					selected={selected}
					total={filtered.length}
					grid={grid}
					kind={kind}
					visible={visible}
					resourceCount={resources.length}
					busy={opening || preference.isPending}
					page={page}
					updateParam={updateParam}
					onOpen={openResource}
					onPin={pinResource}
					onPageChange={(offset) =>
						setParams(
							(previous) => {
								const next = new URLSearchParams(previous);
								next.set("page", String(offset / 12));
								return next;
							},
							{ replace: true },
						)
					}
				/>
			</PageScrollArea>
			{editor && (
				<CollectionEditor
					key={editor === "new" ? "new" : editor.id}
					collection={editor === "new" ? undefined : editor}
					resources={resources}
					isAdmin={isPlatformAdmin}
					onClose={() => setEditor(null)}
					onSave={saveCollection}
					onDelete={deleteCollection}
					busy={busy}
					error={editorError}
				/>
			)}
		</PageWorkspace>
	);
}
