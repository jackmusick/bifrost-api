import { describe, expect, it } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { ExecutionInspector } from "./ExecutionInspector";

describe("ExecutionInspector", () => {
	it("opens on output for completed runs and switches between inspector tabs", async () => {
		const { user } = renderWithProviders(
			<ExecutionInspector
				completed
				output={<div>Rendered output payload</div>}
				input={<div>Submitted input payload</div>}
				details={<div>Run metadata payload</div>}
			/>,
		);

		expect(screen.getByRole("tab", { name: "Output" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Rendered output payload")).toBeVisible();
		expect(
			screen.queryByText("Submitted input payload"),
		).not.toBeInTheDocument();
		expect(
			screen.queryByText("Run metadata payload"),
		).not.toBeInTheDocument();

		await user.click(screen.getByRole("tab", { name: "Input" }));
		expect(screen.getByRole("tab", { name: "Input" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Submitted input payload")).toBeVisible();
		expect(
			screen.queryByText("Rendered output payload"),
		).not.toBeInTheDocument();

		await user.click(screen.getByRole("tab", { name: "Details" }));
		expect(screen.getByRole("tab", { name: "Details" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Run metadata payload")).toBeVisible();
		expect(
			screen.queryByText("Submitted input payload"),
		).not.toBeInTheDocument();
	});

	it("auto-reveals output when a run completes until the user manually selects a tab", async () => {
		const { rerender, user } = renderWithProviders(
			<ExecutionInspector
				completed={false}
				output={<div>Final output</div>}
				input={<div>Original input</div>}
				details={<div>Run details body</div>}
			/>,
		);

		expect(screen.getByRole("tab", { name: "Input" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Original input")).toBeVisible();

		rerender(
			<ExecutionInspector
				completed
				output={<div>Final output</div>}
				input={<div>Original input</div>}
				details={<div>Run details body</div>}
			/>,
		);
		expect(screen.getByRole("tab", { name: "Output" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Final output")).toBeVisible();

		await user.click(screen.getByRole("tab", { name: "Details" }));
		expect(screen.getByText("Run details body")).toBeVisible();

		rerender(
			<ExecutionInspector
				completed={false}
				output={<div>Updated output</div>}
				input={<div>Updated input</div>}
				details={<div>Updated details body</div>}
			/>,
		);
		expect(screen.getByRole("tab", { name: "Details" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Updated details body")).toBeVisible();
		expect(screen.queryByText("Updated input")).not.toBeInTheDocument();
	});

	it("opens on input while a run is still active", () => {
		renderWithProviders(
			<ExecutionInspector
				completed={false}
				output={<div>Pending output</div>}
				input={<div>Live input</div>}
				details={<div>Pending details</div>}
			/>,
		);

		expect(screen.getByRole("tab", { name: "Input" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		expect(screen.getByText("Live input")).toBeVisible();
		expect(screen.queryByText("Pending output")).not.toBeInTheDocument();
	});
});
