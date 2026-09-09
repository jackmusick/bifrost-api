import { describe, expect, it } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { ExecutionActivityTrace } from "./ExecutionActivityTrace";

describe("ExecutionActivityTrace", () => {
	it("shows the active connected stream label for running executions", () => {
		renderWithProviders(
			<ExecutionActivityTrace
				status="Running"
				startedAt="2026-09-08T12:00:00Z"
				executedByName="Alice"
				orgName="Acme"
				isStreamingEnabled
				isConnected
			/>,
		);

		expect(screen.getByLabelText("Execution activity")).toHaveTextContent(
			"Alice · Acme",
		);
		expect(screen.getByText("Live stream connected")).toBeVisible();
	});

	it("shows completed timing without a live stream connection label", () => {
		renderWithProviders(
			<ExecutionActivityTrace
				status="Success"
				startedAt="2026-09-08T12:00:00Z"
				completedAt="2026-09-08T12:03:00Z"
				executedByName="Robin"
				orgName="Global"
				isStreamingEnabled
				isConnected
			/>,
		);

		expect(screen.getByLabelText("Execution activity")).toHaveTextContent(
			"Robin · Global",
		);
		expect(screen.getByText(/^Completed /)).toBeVisible();
		expect(
			screen.queryByText(/Live stream connected|reconnecting|Connecting/),
		).not.toBeInTheDocument();
	});
});
