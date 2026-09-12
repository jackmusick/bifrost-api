import { renderHook } from "@testing-library/react";
import { expect, it, vi } from "vitest";
const { post, invalidate } = vi.hoisted(() => ({ post: vi.fn(), invalidate: vi.fn() }));
vi.mock("@/lib/api-client", () => ({ apiClient: { POST: post } }));
vi.mock("@tanstack/react-query", () => ({ useQueryClient: () => ({ invalidateQueries: invalidate }) }));
import { useAssignEntityRole } from "./useAssignEntityRole";

it("adds roles for each entity type without replacing existing bindings and propagates rejection", async () => {
	post.mockResolvedValue({});
	const { result } = renderHook(() => useAssignEntityRole());
	for (const type of ["workflow", "form", "agent", "app"] as const) await result.current(type, "entity", "role");
	expect(post.mock.calls).toEqual([
		["/api/workflows/{workflow_id}/roles", { params: { path: { workflow_id: "entity" } }, body: { role_ids: ["role"] } }],
		["/api/roles/{role_id}/forms", { params: { path: { role_id: "role" } }, body: { form_ids: ["entity"] } }],
		["/api/roles/{role_id}/agents", { params: { path: { role_id: "role" } }, body: { agent_ids: ["entity"] } }],
		["/api/roles/{role_id}/apps", { params: { path: { role_id: "role" } }, body: { app_ids: ["entity"] } }],
	]);
	expect(invalidate).toHaveBeenCalledTimes(4);
	post.mockResolvedValue({ error: { detail: "Managed entity cannot be changed" } });
	await expect(result.current("workflow", "entity", "role")).rejects.toThrow("Managed entity cannot be changed");
	expect(invalidate).toHaveBeenCalledTimes(4);
});
