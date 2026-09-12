import { useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import { SearchBox } from "@/components/search/SearchBox";
import {
	useRoleKnowledge,
	useAssignKnowledgeToRole,
	useBulkUnassignKnowledge,
} from "@/hooks/useRoles";
import { useOrganizations } from "@/hooks/useOrganizations";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { ConsumerCards } from "./ConsumerCards";
import { KnowledgeAssignDrawer } from "./KnowledgeAssignDrawer";
export function KnowledgeTab({ roleId }: { roleId: string }) {
	const { data, isLoading, isError, isFetching, refetch } =
		useRoleKnowledge(roleId);
	const compact = useMediaQuery("(max-width: 1023px)");
	const [removeFailed, setRemoveFailed] = useState(false);
	const { data: orgs } = useOrganizations();
	const assignMut = useAssignKnowledgeToRole();
	const unassignMut = useBulkUnassignKnowledge();

	const [search, setSearch] = useState("");
	const [selected, setSelected] = useState<Set<string>>(new Set());
	const [drawerOpen, setDrawerOpen] = useState(false);
	const [submitting, setSubmitting] = useState(false);

	const entries = useMemo(() => data?.entries ?? [], [data]);

	const orgName = useMemo(
		() => (orgId?: string | null) => {
			if (!orgId) return "All organizations";
			const o = orgs?.find((x) => x.id === orgId);
			return o?.name || orgId;
		},
		[orgs],
	);

	const visible = useMemo(() => {
		const q = search.trim().toLowerCase();
		if (!q) return entries;
		return entries.filter(
			(e) =>
				e.namespace.toLowerCase().includes(q) ||
				orgName(e.organization_id).toLowerCase().includes(q),
		);
	}, [entries, search, orgName]);

	const visibleIds = useMemo(
		() => new Set(visible.map((e) => e.id)),
		[visible],
	);
	const effective = useMemo(() => {
		const out = new Set<string>();
		for (const id of selected) if (visibleIds.has(id)) out.add(id);
		return out;
	}, [selected, visibleIds]);

	const allSelected =
		visible.length > 0 && visible.every((e) => effective.has(e.id));

	const toggle = (id: string) =>
		setSelected((prev) => {
			const next = new Set<string>();
			for (const s of prev) if (visibleIds.has(s)) next.add(s);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return next;
		});

	const toggleAll = () =>
		setSelected((prev) => {
			const next = new Set<string>();
			for (const s of prev) if (visibleIds.has(s)) next.add(s);
			if (allSelected) {
				for (const e of visible) next.delete(e.id);
			} else {
				for (const e of visible) next.add(e.id);
			}
			return next;
		});

	const handleUnassign = async () => {
		const ids = Array.from(effective);
		if (ids.length === 0 || submitting) return;
		setRemoveFailed(false);
		setSubmitting(true);
		try {
			await unassignMut.mutateAsync({
				params: { path: { role_id: roleId } },
				body: { assignment_ids: ids },
			});
			toast.success(`Removed ${ids.length} knowledge assignment(s)`);
			setSelected(new Set());
		} catch (e) {
			setRemoveFailed(true);
			toast.error(
				e instanceof Error ? e.message : "Failed to remove knowledge",
			);
		} finally {
			setSubmitting(false);
		}
	};

	return (
		<div className="flex min-w-0 flex-col gap-4 lg:min-h-0 lg:flex-1">
			<div className="flex flex-col gap-3 sm:flex-row sm:items-center">
				<SearchBox
					value={search}
					onChange={setSearch}
					placeholder="Search namespaces..."
					className="min-w-0 flex-1 [&_input]:h-11"
				/>
				<Button
					className="min-h-11"
					onClick={() => setDrawerOpen(true)}
				>
					<Plus className="h-4 w-4 mr-1.5" />
					Assign namespace
				</Button>
			</div>

			{isError && (
				<div
					role="alert"
					className="space-y-2 rounded-[var(--bf-radius-surface)] border p-4 text-sm"
				>
					<p>
						{data
							? "Knowledge assignments could not refresh. Previously loaded assignments are shown."
							: "Knowledge assignments could not load."}
					</p>
					<Button
						variant="outline"
						className="min-h-11"
						disabled={isFetching}
						onClick={() => void refetch()}
					>
						Retry knowledge assignments
					</Button>
				</div>
			)}
			{removeFailed && (
				<p role="alert" className="text-sm text-destructive">
					Assignments could not be removed. Your selection is
					retained; try again.
				</p>
			)}
			{isLoading ? (
				<div className="space-y-2">
					{[...Array(3)].map((_, i) => (
						<Skeleton key={i} className="h-12 w-full" />
					))}
				</div>
			) : isError && !data ? null : visible.length === 0 ? (
				<div className="text-sm text-muted-foreground py-8 text-center rounded-[var(--bf-radius-surface)] border border-dashed">
					{search.trim()
						? "No assigned namespaces match your search."
						: "No knowledge namespaces assigned to this role yet."}
				</div>
			) : compact ? (
				<ConsumerCards
					items={visible.map((e) => ({
						id: e.id,
						primary: e.namespace,
						secondary: `Scope: ${orgName(e.organization_id)}`,
					}))}
					selected={effective}
					label="namespaces"
					allSelected={allSelected}
					someSelected={effective.size > 0}
					pending={submitting}
					hideSecondary={false}
					showOrg={false}
					onToggle={toggle}
					onToggleAll={toggleAll}
				/>
			) : (
				<DataTable className="max-h-full">
					<DataTableHeader>
						<DataTableRow>
							<DataTableHead className="w-0 whitespace-nowrap">
								<Checkbox
									disabled={submitting}
									checked={
										allSelected
											? true
											: effective.size > 0
												? "indeterminate"
												: false
									}
									onCheckedChange={toggleAll}
									aria-label="Select all visible namespaces"
								/>
							</DataTableHead>
							<DataTableHead>Namespace</DataTableHead>
							<DataTableHead className="w-0 whitespace-nowrap">
								Scope
							</DataTableHead>
						</DataTableRow>
					</DataTableHeader>
					<DataTableBody>
						{visible.map((e) => (
							<DataTableRow key={e.id}>
								<DataTableCell className="w-0 whitespace-nowrap">
									<Checkbox
										disabled={submitting}
										checked={effective.has(e.id)}
										onCheckedChange={() => toggle(e.id)}
										aria-label={`Select ${e.namespace}`}
									/>
								</DataTableCell>
								<DataTableCell className="font-medium">
									{e.namespace}
								</DataTableCell>
								<DataTableCell className="w-0 whitespace-nowrap text-sm text-muted-foreground">
									{orgName(e.organization_id)}
								</DataTableCell>
							</DataTableRow>
						))}
					</DataTableBody>
				</DataTable>
			)}

			{effective.size > 0 && (
				<div
					role="region"
					aria-label="Selected namespaces"
					className="sticky bottom-2 flex flex-wrap items-center gap-3 rounded-[var(--bf-radius-surface)] bg-popover px-4 py-2 shadow-lg ring-1 ring-foreground/5 dark:ring-foreground/10"
				>
					<span className="text-sm font-medium">
						{effective.size} selected
					</span>
					<Button
						variant="destructive"
						size="sm"
						className="min-h-11"
						disabled={submitting}
						onClick={handleUnassign}
					>
						{submitting ? "Unassigning..." : "Unassign from role"}
					</Button>
					<Button
						variant="ghost"
						size="sm"
						className="ml-auto min-h-11"
						disabled={submitting}
						onClick={() => setSelected(new Set())}
					>
						Clear
					</Button>
				</div>
			)}

			{drawerOpen && (
				<KnowledgeAssignDrawer
					roleId={roleId}
					onClose={() => setDrawerOpen(false)}
					onAssign={async (entries) => {
						await assignMut.mutateAsync({
							params: { path: { role_id: roleId } },
							body: { entries },
						});
					}}
				/>
			)}
		</div>
	);
}
