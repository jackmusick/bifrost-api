import { expect, it, vi } from "vitest";
import { deleteEntities } from "./deleteEntities";
import { authFetch } from "@/lib/api-client";
vi.mock("@/lib/api-client", () => ({ authFetch: vi.fn() }));
it("keeps successful deletes, retryable failures and workflow conflicts separate", async () => {
	const fetch = vi.mocked(authFetch);
	fetch.mockReset();
	fetch
		.mockResolvedValueOnce(new Response(null, { status: 204 }))
		.mockResolvedValueOnce(
			new Response(
				JSON.stringify({ detail: { message: "Service unavailable" } }),
				{ status: 500 },
			),
		)
		.mockResolvedValueOnce(
			new Response(
				JSON.stringify({
					pending_deactivations: [],
					available_replacements: [],
				}),
				{ status: 409 },
			),
		);
	const entities = [
		{ id: "app", name: "App", entityType: "app" as const },
		{ id: "form", name: "Form", entityType: "form" as const },
		{ id: "workflow", name: "Workflow", entityType: "workflow" as const },
	];
	const result = await deleteEntities(entities);
	expect(result.deletedIds).toEqual(["app"]);
	expect(result.deletedKeys).toEqual(["app:app"]);
	expect(result.failures).toEqual([
		{ entity: entities[1], message: "Service unavailable" },
	]);
	expect(result.conflictIds).toEqual(["workflow"]);
	fetch.mockResolvedValueOnce(new Response(null, { status: 204 }));
	await deleteEntities(result.failures.map((failure) => failure.entity));
	expect(fetch.mock.calls.map(([url]) => url)).toEqual([
		"/api/applications/app",
		"/api/forms/form",
		"/api/workflows/workflow",
		"/api/forms/form",
	]);
	expect(fetch.mock.calls[2][1]).toMatchObject({ body: "{}" });
});
it("continues after network and non-JSON failures", async () => {
	const fetch = vi.mocked(authFetch);
	fetch.mockReset();
	fetch
		.mockRejectedValueOnce(new Error("Network unavailable"))
		.mockResolvedValueOnce(new Response("Bad gateway", { status: 500 }));
	const result = await deleteEntities([
		{ id: "a", name: "A", entityType: "agent" },
		{ id: "b", name: "B", entityType: "form" },
	]);
	expect(result.failures.map((f) => f.message)).toEqual([
		"Network unavailable",
		"Deletion failed. Try again.",
	]);
});
