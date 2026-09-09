import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseQuery = vi.fn();

vi.mock("@/lib/api-client", () => ({
	$api: { useQuery: (...args: unknown[]) => mockUseQuery(...args) },
}));

import { useAuditLog } from "./useAuditLog";

describe("useAuditLog", () => {
	beforeEach(() => {
		mockUseQuery.mockReset();
	});

	it("preserves previous page data only when non-token filters match", () => {
		const previousData = { entries: [{ id: "page-one" }] };
		const previousQuery = {
			queryKey: [
				"get",
				"/api/audit",
				{
					params: {
						query: {
							action: "policy.deny",
							limit: 50,
							continuation_token: "first-token",
						},
					},
				},
			],
		};

		useAuditLog(
			{
				action: "policy.deny",
				limit: 50,
				continuation_token: "second-token",
			},
			true,
			{ preservePageData: true },
		);

		const options = mockUseQuery.mock.calls[0][3];
		expect(options.placeholderData(previousData, previousQuery)).toBe(
			previousData,
		);

		useAuditLog(
			{
				action: "organization.update",
				limit: 50,
				continuation_token: "second-token",
			},
			true,
			{ preservePageData: true },
		);

		const changedFilterOptions = mockUseQuery.mock.calls[1][3];
		expect(
			changedFilterOptions.placeholderData(previousData, previousQuery),
		).toBeUndefined();
	});
});
