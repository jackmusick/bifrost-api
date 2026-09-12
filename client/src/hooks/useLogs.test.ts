import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseQuery = vi.fn();

vi.mock("@/lib/api-client", () => ({
	$api: { useQuery: (...args: unknown[]) => mockUseQuery(...args) },
}));

import { useLogs } from "./useLogs";

describe("useLogs", () => {
	beforeEach(() => {
		mockUseQuery.mockReset();
	});

	it("preserves previous log page data only when non-token filters match", () => {
		const previousData = {
			logs: [{ id: "log-one" }],
			continuation_token: "next",
		};
		const previousQuery = {
			queryKey: [
				"get",
				"/api/executions/logs",
				{
					params: {
						query: {
							organization_id: "org-1",
							levels: "ERROR",
							continuation_token: "first",
						},
					},
				},
			],
		};

		useLogs({ organization_id: "org-1", levels: "ERROR" }, "second", true, {
			preservePageData: true,
		});

		expect(
			mockUseQuery.mock.calls[0][3].placeholderData(
				previousData,
				previousQuery,
			),
		).toBe(previousData);

		useLogs({ organization_id: "org-2", levels: "ERROR" }, "second", true, {
			preservePageData: true,
		});

		expect(
			mockUseQuery.mock.calls[1][3].placeholderData(
				previousData,
				previousQuery,
			),
		).toBeUndefined();
	});
});
