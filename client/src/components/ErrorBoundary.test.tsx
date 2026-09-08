import { Component } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ErrorBoundary } from "./ErrorBoundary";

class ThrowingChild extends Component<{ shouldThrow: boolean }> {
	render() {
		if (this.props.shouldThrow) {
			throw new Error("Boom");
		}
		return <div>Safe content</div>;
	}
}

describe("ErrorBoundary", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("renders a readable fallback with recovery actions", () => {
		const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

		render(
			<ErrorBoundary>
				<ThrowingChild shouldThrow={true} />
			</ErrorBoundary>,
		);

		expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
		expect(screen.getByText("Boom")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /go to home/i })).toBeInTheDocument();
		expect(consoleSpy).toHaveBeenCalled();
	});

	it("restores the child tree when Try Again is clicked", () => {
		const Wrapper = ({ shouldThrow }: { shouldThrow: boolean }) => (
			<ErrorBoundary>
				<ThrowingChild shouldThrow={shouldThrow} />
			</ErrorBoundary>
		);

		const { rerender } = render(<Wrapper shouldThrow={true} />);
		expect(screen.getByText("Something went wrong")).toBeInTheDocument();

		rerender(<Wrapper shouldThrow={false} />);
		fireEvent.click(screen.getByRole("button", { name: /try again/i }));

		return waitFor(() => {
			expect(screen.getByText("Safe content")).toBeInTheDocument();
		});
	});
});
