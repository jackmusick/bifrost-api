import { it, expect, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { LogLevel, LogRecord } from "./LogRecord";

it("renders semantic severities for log badges", () => {
	renderWithProviders(
		<div className="space-y-2">
			<LogLevel level="INFO" />
			<LogLevel level="WARNING" />
			<LogLevel level="ERROR" />
		</div>,
	);

	expect(screen.getByText("INFO")).toHaveClass("text-[var(--bf-info)]");
	expect(screen.getByText("WARNING")).toHaveClass("text-[var(--bf-warning)]");
	expect(screen.getByText("ERROR")).toHaveClass("text-[var(--bf-danger)]");
});

it("opens a log record when its workflow link is activated", async () => {
	const onOpen = vi.fn();
	const { user } = renderWithProviders(
		<LogRecord
			log={
				{
					execution_id: "run-123",
					workflow_name: "workflow-a",
					organization_name: "Tenant A",
					executed_by_name: "Test User",
					level: "INFO",
					message: "Created execution",
					timestamp: "2026-09-07T12:00:00Z",
				} as never
			}
			onOpen={onOpen}
		/>,
	);

	await user.click(screen.getByRole("link", { name: "workflow-a" }));
	expect(onOpen).toHaveBeenCalledWith(
		expect.objectContaining({ execution_id: "run-123" }),
	);
});
