import { describe, expect, it } from "vitest";

import {
	samePathAndBodyExcept,
	sameQueryParamsExcept,
} from "./paginated-query";

describe("paginated query retention guards", () => {
	it("matches query params regardless of key order while excluding page tokens", () => {
		const previousQuery = {
			queryKey: [
				"get",
				"/api/audit",
				{
					params: {
						query: {
							search: "policy",
							action: "policy.deny",
							continuation_token: "one",
						},
					},
				},
			],
		};

		expect(
			sameQueryParamsExcept(
				{
					action: "policy.deny",
					search: "policy",
					continuation_token: "two",
				},
				previousQuery,
				["continuation_token"],
			),
		).toBe(true);
		expect(
			sameQueryParamsExcept(
				{
					action: "user.update",
					search: "policy",
					continuation_token: "two",
				},
				previousQuery,
				["continuation_token"],
			),
		).toBe(false);
	});

	it("requires the same path and same non-offset body for document pages", () => {
		const previousQuery = {
			queryKey: [
				"post",
				"/api/tables/{table_id}/documents/query",
				{
					params: { path: { table_id: "table-1" } },
					body: {
						where: { status: { eq: "active" } },
						limit: 25,
						offset: 0,
					},
				},
			],
		};

		expect(
			samePathAndBodyExcept(
				{ table_id: "table-1" },
				{ where: { status: { eq: "active" } }, limit: 25, offset: 25 },
				previousQuery,
				["offset"],
			),
		).toBe(true);
		expect(
			samePathAndBodyExcept(
				{ table_id: "table-2" },
				{ where: { status: { eq: "active" } }, limit: 25, offset: 25 },
				previousQuery,
				["offset"],
			),
		).toBe(false);
	});
});
