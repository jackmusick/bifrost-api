import { Component } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { PageErrorBoundary } from "./PageErrorBoundary";

class ThrowingChild extends Component<{ shouldThrow: boolean }> {
	render() {
		if (this.props.shouldThrow) {
			throw new Error("Route crashed");
		}
		return <div>Route content</div>;
	}
}

describe("PageErrorBoundary", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("renders a route error card with a retry action", () => {
		render(
			<PageErrorBoundary>
				<ThrowingChild shouldThrow={true} />
			</PageErrorBoundary>,
		);

		expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
		expect(screen.getByText("Route crashed")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
	});

	it("resets when the route key changes", () => {
		const { rerender } = render(
			<PageErrorBoundary resetKey="/one">
				<ThrowingChild shouldThrow={true} />
			</PageErrorBoundary>,
		);

		expect(screen.getByText("Something went wrong")).toBeInTheDocument();
		rerender(
			<PageErrorBoundary resetKey="/two">
				<ThrowingChild shouldThrow={false} />
			</PageErrorBoundary>,
		);

		expect(screen.getByText("Route content")).toBeInTheDocument();
	});

	it("lets the retry button clear the error state", () => {
		const { rerender } = render(
			<PageErrorBoundary>
				<ThrowingChild shouldThrow={true} />
			</PageErrorBoundary>,
		);

		rerender(
			<PageErrorBoundary>
				<ThrowingChild shouldThrow={false} />
			</PageErrorBoundary>,
		);
		fireEvent.click(screen.getByRole("button", { name: /try again/i }));

		return waitFor(() => {
			expect(screen.getByText("Route content")).toBeInTheDocument();
		});
	});
});
