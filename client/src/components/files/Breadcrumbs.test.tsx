import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
const mobile = vi.fn(() => false);
vi.mock("@/hooks/useMediaQuery", () => ({ useMediaQuery: () => mobile() }));
import { Breadcrumbs } from "./Breadcrumbs";

describe("Breadcrumbs", () => {
	it("renders scope + location + segments and navigates", () => {
		const onNavigate = vi.fn();
		render(
			<Breadcrumbs
				scopeLabel="Global"
				location="gallery"
				segments={["team", "q1"]}
				onNavigate={onNavigate}
			/>,
		);
		expect(screen.getByText("Global")).toBeInTheDocument();
		expect(screen.getByText("gallery")).toBeInTheDocument();
		expect(screen.getByRole("list")).toHaveClass("overflow-x-auto");
		fireEvent.click(screen.getByText("team"));
		expect(onNavigate).toHaveBeenCalledWith(1);
		fireEvent.click(screen.getByText("gallery"));
		expect(onNavigate).toHaveBeenCalledWith(0);
		fireEvent.click(screen.getByText("Global"));
		expect(onNavigate).toHaveBeenCalledWith(-1);
	});

	it("shows only the scope at the shares root", () => {
		render(
			<Breadcrumbs
				scopeLabel="Acme"
				location={null}
				segments={[]}
				onNavigate={vi.fn()}
			/>,
		);
		expect(screen.getByText("Acme")).toBeInTheDocument();
		expect(screen.queryByText("gallery")).not.toBeInTheDocument();
	});
	it("keeps the current folder visible on mobile and exposes every ancestor", async () => {
		mobile.mockReturnValue(true);
		const onNavigate = vi.fn();
		render(
			<Breadcrumbs
				scopeLabel="Global"
				location="gallery"
				segments={["team", "reports"]}
				onNavigate={onNavigate}
			/>,
		);
		expect(screen.getByRole("button", { name: "reports" })).toHaveAttribute(
			"aria-current",
			"location",
		);
		expect(screen.getByRole("button", { name: "reports" })).toHaveClass(
			"truncate",
		);
		expect(
			screen.queryByRole("button", { name: "team" }),
		).not.toBeInTheDocument();
		fireEvent.pointerDown(
			screen.getByRole("button", { name: "Parent locations" }),
			{ button: 0, ctrlKey: false },
		);
		expect(
			await screen.findByRole("menuitem", { name: "Global" }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("menuitem", { name: "gallery" }),
		).toBeInTheDocument();
		fireEvent.click(screen.getByRole("menuitem", { name: "team" }));
		expect(onNavigate).toHaveBeenCalledWith(1);
		mobile.mockReturnValue(false);
	});
	it("omits the scope root for solution navigation without changing folder depths", () => {
		const onNavigate = vi.fn();
		render(
			<Breadcrumbs
				scopeLabel="Finance Ops"
				includeScopeRoot={false}
				location="gallery"
				segments={["team"]}
				onNavigate={onNavigate}
			/>,
		);
		expect(screen.queryByText("Finance Ops")).not.toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "gallery" }));
		expect(onNavigate).toHaveBeenCalledWith(0);
		fireEvent.click(screen.getByRole("button", { name: "team" }));
		expect(onNavigate).toHaveBeenCalledWith(1);
	});
});
