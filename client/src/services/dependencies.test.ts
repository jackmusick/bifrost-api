import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPost = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", () => ({
	apiClient: { POST: (...args: unknown[]) => mockPost(...args) },
}));

import { getDependencyAvailability } from "./dependencies";

describe("getDependencyAvailability", () => {
	beforeEach(() => {
		mockPost.mockReset();
	});

	it("posts the availability request and forwards abort signals", async () => {
		mockPost.mockResolvedValue({
			data: { has_relationships: { "app:app-1": false } },
		});
		const controller = new AbortController();
		const request = {
			workflow_ids: ["workflow-1"],
			form_ids: ["form-1"],
			app_ids: ["app-1"],
			agent_ids: [],
		};

		await expect(
			getDependencyAvailability(request, { signal: controller.signal }),
		).resolves.toEqual({
			has_relationships: { "app:app-1": false },
		});
		expect(mockPost).toHaveBeenCalledWith(
			"/api/dependencies/availability",
			{
				body: request,
				signal: controller.signal,
			},
		);
	});

	it("throws on API errors", async () => {
		mockPost.mockResolvedValue({
			error: { detail: "relationship lookup failed" },
		});

		await expect(
			getDependencyAvailability({
				workflow_ids: [],
				form_ids: [],
				app_ids: [],
				agent_ids: [],
			}),
		).rejects.toThrow("relationship lookup failed");
	});
});
