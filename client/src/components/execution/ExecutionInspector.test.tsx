import { describe, expect, it } from "vitest";
import { useState } from "react";
import { renderWithProviders, screen } from "@/test-utils";
import { ExecutionInspector } from "./ExecutionInspector";

describe("ExecutionInspector", () => {
	it("opens on result and switches between execution content tabs", async () => {
		const { user } = renderWithProviders(
			<ExecutionInspector
				result={<div>Rendered result payload</div>}
				input={<div>Submitted input payload</div>}
				logs={<div>Run logs payload</div>}
			/>,
		);

		expect(screen.getByLabelText("Execution content")).toBeInTheDocument();
		expect(screen.getByRole("tab", { name: "Result" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Rendered result payload")).toBeVisible();
		expect(
			screen.queryByText("Submitted input payload"),
		).not.toBeInTheDocument();
		expect(screen.queryByText("Run logs payload")).not.toBeInTheDocument();

		await user.click(screen.getByRole("tab", { name: "Input" }));
		expect(screen.getByRole("tab", { name: "Input" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Submitted input payload")).toBeVisible();
		expect(
			screen.queryByText("Rendered result payload"),
		).not.toBeInTheDocument();

		await user.click(screen.getByRole("tab", { name: "Logs" }));
		expect(screen.getByRole("tab", { name: "Logs" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Run logs payload")).toBeVisible();
		expect(
			screen.queryByText("Submitted input payload"),
		).not.toBeInTheDocument();
	});

	it("keeps a manual logs selection across content updates", async () => {
		const { rerender, user } = renderWithProviders(
			<ExecutionInspector
				result={<div>Final result</div>}
				input={<div>Original input</div>}
				logs={<div>Run logs body</div>}
			/>,
		);

		expect(screen.getByRole("tab", { name: "Result" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Final result")).toBeVisible();

		await user.click(screen.getByRole("tab", { name: "Logs" }));
		expect(screen.getByText("Run logs body")).toBeVisible();

		rerender(
			<ExecutionInspector
				result={<div>Updated result</div>}
				input={<div>Updated input</div>}
				logs={<div>Updated logs body</div>}
			/>,
		);
		expect(screen.getByRole("tab", { name: "Logs" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Updated logs body")).toBeVisible();
		expect(screen.queryByText("Updated input")).not.toBeInTheDocument();
	});

	it("supports controlled tab changes from parent actions", async () => {
		const Wrapper = () => {
			const [tab, setTab] = useState<"result" | "input" | "logs">(
				"result",
			);
			return (
				<>
					<button type="button" onClick={() => setTab("logs")}>
						View logs
					</button>
					<ExecutionInspector
						value={tab}
						onValueChange={setTab}
						result={<div>Pending result</div>}
						input={<div>Live input</div>}
						logs={<div>Pending logs</div>}
					/>
				</>
			);
		};
		const { user } = renderWithProviders(<Wrapper />);

		expect(screen.getByRole("tab", { name: "Result" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		await user.click(screen.getByRole("button", { name: "View logs" }));
		expect(screen.getByRole("tab", { name: "Logs" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Pending logs")).toBeVisible();
	});

	it("renders collapsed summary below the selected content", () => {
		renderWithProviders(
			<ExecutionInspector
				result={<div>Primary result</div>}
				input={<div>Live input</div>}
				logs={<div>Pending logs</div>}
				summary={<button type="button">More details</button>}
			/>,
		);

		const result = screen.getByText("Primary result");
		const summary = screen.getByRole("button", { name: "More details" });
		expect(
			result.compareDocumentPosition(summary) &
				Node.DOCUMENT_POSITION_FOLLOWING,
		).toBeTruthy();
	});
});
