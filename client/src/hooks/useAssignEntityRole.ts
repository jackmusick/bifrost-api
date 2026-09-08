import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { EntityType } from "@/components/entity-management/types";

/** Add one role through additive endpoints; never replace existing role bindings. */
export function useAssignEntityRole() {
	const queryClient = useQueryClient();
	return useCallback(async (entityType: EntityType, entityId: string, roleId: string) => {
		const result = entityType === "workflow"
			? await apiClient.POST("/api/workflows/{workflow_id}/roles", { params: { path: { workflow_id: entityId } }, body: { role_ids: [roleId] } })
			: entityType === "form"
				? await apiClient.POST("/api/roles/{role_id}/forms", { params: { path: { role_id: roleId } }, body: { form_ids: [entityId] } })
				: entityType === "agent"
					? await apiClient.POST("/api/roles/{role_id}/agents", { params: { path: { role_id: roleId } }, body: { agent_ids: [entityId] } })
					: await apiClient.POST("/api/roles/{role_id}/apps", { params: { path: { role_id: roleId } }, body: { app_ids: [entityId] } });
		if (result.error) throw new Error(typeof result.error.detail === "string" ? result.error.detail : "Could not add the selected role.");
		void queryClient.invalidateQueries({ predicate: query => typeof query.queryKey[1] === "string" && query.queryKey[1].includes("/roles") });
	}, [queryClient]);
}
