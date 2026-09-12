import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders, screen } from "@/test-utils";
import type { components } from "@/lib/v1";

import { AgentActivityWorkspace } from "./AgentActivityWorkspace";

vi.mock("@/components/agents/Timeline", () => ({
	Timeline: (props: {
		steps: unknown[];
		inspector?: string;
		joinedRows?: boolean;
		toolbarActions?: ReactNode;
	}) => (
		<div
			role="region"
			aria-label="Timeline"
			data-inspector={props.inspector}
			data-joined-rows={props.joinedRows ? "true" : "false"}
			data-steps={props.steps.length}
		>
			{props.toolbarActions}
			Timeline
		</div>
	),
	AdvancedTimeline: (props: { steps: unknown[] }) => (
		<div
			role="region"
			aria-label="Advanced timeline"
			data-steps={props.steps.length}
		>
			Advanced timeline
		</div>
	),
}));

vi.mock("@/components/agents/RunReviewPanel", () => ({
	RunPayloads: ({
		input,
		output,
	}: {
		input: Record<string, unknown>;
		output: Record<string, unknown>;
	}) => (
		<div role="region" aria-label="Run payloads">
			{String(input.ticket_id)} {String(output.routed)}
		</div>
	),
}));

type Run = components["schemas"]["AgentRunDetailResponse"];

const run = {
	id: "run-1",
	agent_id: "agent-1",
	agent_name: "Triage",
	trigger_type: "manual",
	status: "completed",
	summary_status: "completed",
	iterations_used: 2,
	tokens_used: 100,
	asked: "Triage ticket",
	did: "Routed it",
	input: { ticket_id: 428950 },
	output: { routed: true },
	metadata: {},
	created_at: "2026-04-20T12:00:00Z",
	steps: [
		{
			id: "step-1",
			run_id: "run-1",
			step_number: 1,
			type: "tool_call",
			content: { tool_name: "get_ticket" },
			created_at: "2026-04-20T12:00:00Z",
		},
	],
	child_run_ids: [],
	child_runs: [],
} satisfies Run;

describe("AgentActivityWorkspace", () => {
	it("renders the normal timeline inline before Advanced is enabled", () => {
		renderWithProviders(<AgentActivityWorkspace run={run} />);

		expect(
			screen.getByRole("region", { name: "Timeline" }),
		).toHaveAttribute("data-inspector", "inline");
		expect(
			screen.getByRole("region", { name: "Timeline" }),
		).toHaveAttribute("data-joined-rows", "true");
		expect(
			screen.getByRole("region", { name: "Timeline" }),
		).toHaveAttribute("data-steps", "1");
		expect(
			screen.queryByRole("region", { name: "Run payloads" }),
		).not.toBeInTheDocument();
	});

	it("keeps Advanced as local content with payloads and raw trace", async () => {
		const { user } = renderWithProviders(
			<AgentActivityWorkspace run={run} />,
		);

		await user.click(screen.getByRole("button", { name: /advanced/i }));
		expect(
			screen.getByRole("button", { name: /advanced/i }),
		).toHaveAttribute("aria-pressed", "true");
		expect(
			screen.getByRole("region", { name: "Run payloads" }),
		).toHaveTextContent("428950 true");
		expect(screen.getByText("Raw executor trace")).toBeInTheDocument();
		expect(
			screen.getByRole("region", { name: "Advanced timeline" }),
		).toHaveAttribute("data-steps", "1");
		expect(
			screen.queryByRole("region", { name: "Timeline" }),
		).not.toBeInTheDocument();
	});
});
