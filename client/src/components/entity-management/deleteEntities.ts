import { authFetch } from "@/lib/api-client";
import { getErrorMessage } from "@/lib/api-error";
import type { components } from "@/lib/v1";
import type { DeleteConfirmEntity } from "./DeleteConfirmDialog";

/** Preserve partial success so retry never repeats an already completed delete. */
export async function deleteEntities(entities: DeleteConfirmEntity[]) {
	const deletedIds: string[] = [];
	const deletedKeys: string[] = [];
	const failures: { entity: DeleteConfirmEntity; message: string }[] = [];
	const conflictIds: string[] = [];
	const pendingDeactivations: components["schemas"]["PendingDeactivation"][] =
		[];
	const availableReplacements: components["schemas"]["AvailableReplacement"][] =
		[];
	for (const entity of entities) {
		try {
			const collection = {
				workflow: "workflows",
				form: "forms",
				agent: "agents",
				app: "applications",
			}[entity.entityType];
			const response = await authFetch(
				`/api/${collection}/${entity.id}`,
				{
					method: "DELETE",
					...(entity.entityType === "workflow"
						? {
								headers: { "Content-Type": "application/json" },
								body: JSON.stringify({}),
							}
						: {}),
				},
			);
			if (entity.entityType === "workflow" && response.status === 409) {
				const conflict = await response.json();
				conflictIds.push(entity.id);
				pendingDeactivations.push(
					...(conflict.pending_deactivations ?? []),
				);
				availableReplacements.push(
					...(conflict.available_replacements ?? []),
				);
			} else if (response.ok) {
				deletedIds.push(entity.id);
				deletedKeys.push(`${entity.entityType}:${entity.id}`);
			} else
				throw new Error(
					getErrorMessage(
						await response
							.json()
							.then((body) =>
								typeof body.detail === "string"
									? new Error(body.detail)
									: body.detail,
							)
							.catch(() => null),
						"Deletion failed. Try again.",
					),
				);
		} catch (error) {
			failures.push({
				entity,
				message:
					error instanceof Error
						? error.message
						: "Deletion failed. Try again.",
			});
		}
	}
	return {
		deletedIds,
		deletedKeys,
		failures,
		conflictIds,
		pendingDeactivations,
		availableReplacements,
	};
}
