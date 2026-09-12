/**
 * Component tests for AppLoadingSkeleton.
 *
 * This is mostly a layout/presentational component, but it exposes one
 * small piece of behavior — the optional `message` prop that appears
 * alongside the spinner. Cover both the default and an explicit override
 * so regressions in the prop wiring surface as a failing test.
 */

import { describe, it, expect } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { AppLoadingSkeleton } from "./AppLoadingSkeleton";

describe("AppLoadingSkeleton", () => {
	it("shows the default 'Loading application...' message", () => {
		renderWithProviders(<AppLoadingSkeleton />);
		expect(screen.getByText(/loading application/i)).toBeInTheDocument();
	});

	it("uses a caller-provided message when one is passed", () => {
		renderWithProviders(
			<AppLoadingSkeleton message="Booting widgets..." />,
		);
		expect(screen.getByText("Booting widgets...")).toBeInTheDocument();
		expect(
			screen.queryByText(/loading application/i),
		).not.toBeInTheDocument();
	});
	it("shows known app identity and logo without inventing progress", () => {
		const { container } = renderWithProviders(
			<AppLoadingSkeleton
				appName="Dispatch Board"
				appLogo="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E"
			/>,
		);

		expect(screen.getByRole("status")).toHaveAccessibleName(
			"Opening Dispatch Board…",
		);
		expect(screen.getByText("Dispatch Board")).toBeInTheDocument();
		expect(screen.getByText("Opening Dispatch Board…")).toBeInTheDocument();
		expect(container.querySelector("img")).toHaveAttribute(
			"src",
			"data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E",
		);
		expect(
			screen.queryByText(/stage|percent|step/i),
		).not.toBeInTheDocument();
	});

	it("uses an initial when the app has no logo", () => {
		renderWithProviders(<AppLoadingSkeleton appName="Quotes" />);
		expect(screen.getByText("Q")).toBeInTheDocument();
		expect(screen.getByText("Opening Quotes…")).toBeInTheDocument();
	});
});
