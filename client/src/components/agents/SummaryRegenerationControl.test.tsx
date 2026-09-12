import { act, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { SummaryRegenerationControl } from "./SummaryRegenerationControl";

const mutate = vi.hoisted(() => vi.fn());
vi.mock("@/services/agentRuns", () => ({
	useRegenerateSummary: () => ({ mutate, isPending: false }),
}));

describe("SummaryRegenerationControl", () => {
	it("guards repeated requests and makes a failed request retryable", () => {
		mutate.mockClear();
		renderWithProviders(
			<SummaryRegenerationControl
				runId="run-one"
				allowed
				testId="regenerate"
			/>,
		);
		const button = screen.getByTestId("regenerate");
		fireEvent.click(button);
		fireEvent.click(button);
		expect(mutate).toHaveBeenCalledTimes(1);
		const callbacks = mutate.mock.calls[0][1];
		act(() => {
			callbacks.onError();
			callbacks.onSettled();
		});
		expect(screen.getByRole("alert")).toHaveFocus();
		expect(button).toHaveTextContent("Retry regeneration");
		fireEvent.click(button);
		expect(mutate).toHaveBeenCalledTimes(2);
		expect(mutate.mock.calls[1][0]).toEqual({
			params: { path: { run_id: "run-one" } },
		});
		expect(screen.queryByRole("alert")).not.toBeInTheDocument();
	});

	it("does not submit for a user without permission", () => {
		mutate.mockClear();
		renderWithProviders(
			<SummaryRegenerationControl
				runId="run-one"
				allowed={false}
				testId="regenerate"
			/>,
		);
		fireEvent.click(screen.getByTestId("regenerate"));
		expect(mutate).not.toHaveBeenCalled();
	});
});
