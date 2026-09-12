import { describe, expect, it } from "vitest";
import { generateUsageDemoData } from "./UsageReports.demo";

const orgs = [
	{ id: "org-a", name: "Alpha" },
	{ id: "org-b", name: "Beta" },
	{ id: "org-c", name: "Gamma" },
];

describe("generateUsageDemoData", () => {
	it("populates agent rows and keeps org execution counts tied to workflow executions only", () => {
		const data = generateUsageDemoData({
			startDate: "2026-08-01",
			endDate: "2026-08-31",
			orgId: null,
			source: "agents",
			realOrgs: orgs,
		});

		expect(data.by_agent).toBeDefined();
		expect(data.by_agent).not.toHaveLength(0);
		expect(data.by_workflow).toBeUndefined();
		expect(data.by_conversation).toBeUndefined();
		expect(Number(data.summary.total_ai_cost)).toBeGreaterThan(0);
		expect(data.summary.total_ai_calls).toBeGreaterThan(0);
		expect(data.summary.total_cpu_seconds).toBe(0);
		expect(data.summary.peak_memory_bytes).toBe(0);

		for (const org of data.by_organization ?? []) {
			expect(org.execution_count).toBe(0);
			expect(org.conversation_count).toBe(0);
			expect(Number(org.ai_cost)).toBeGreaterThan(0);
			expect(org.input_tokens).toBeGreaterThan(0);
			expect(org.output_tokens).toBeGreaterThan(0);
		}
	});

	it("keeps demo trend buckets inside the selected calendar dates", () => {
		const data = generateUsageDemoData({
			startDate: "2026-08-01",
			endDate: "2026-08-03",
			orgId: null,
			source: "agents",
			realOrgs: orgs,
		});
		expect(data.trends?.map((entry) => entry.date)).toEqual([
			"2026-08-01",
			"2026-08-02",
			"2026-08-03",
		]);
	});

	it("scopes every generated section to the selected organization", () => {
		const data = generateUsageDemoData({
			startDate: "2026-08-01",
			endDate: "2026-08-31",
			orgId: "org-b",
			source: "all",
			realOrgs: orgs,
		});

		expect(data.by_organization).toHaveLength(1);
		expect(data.by_organization![0].organization_id).toBe("org-b");

		for (const workflow of data.by_workflow ?? []) {
			expect(
				(workflow as { organization_id?: string }).organization_id,
			).toBe("org-b");
		}
		for (const conversation of data.by_conversation ?? []) {
			expect(
				(conversation as { organization_id?: string }).organization_id,
			).toBe("org-b");
		}
		for (const agent of data.by_agent ?? []) {
			expect(
				(agent as { organization_id?: string }).organization_id,
			).toBe("org-b");
		}
	});
});
