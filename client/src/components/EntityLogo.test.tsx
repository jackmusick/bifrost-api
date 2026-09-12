import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { EntityLogo } from "./EntityLogo";

describe("EntityLogo", () => {
	it("renders an img tag pointing at the entity logo endpoint", () => {
		render(
			<EntityLogo
				entityType="app"
				entityId="11111111-1111-1111-1111-111111111111"
				fallback={<span data-testid="fallback">F</span>}
				size={32}
			/>,
		);
		const img = screen.getByTestId("entity-logo");
		expect(img.getAttribute("src")).toContain(
			"/api/applications/11111111-1111-1111-1111-111111111111/logo",
		);
	});

	it("uses the agents endpoint for entityType=agent", () => {
		render(
			<EntityLogo
				entityType="agent"
				entityId="22222222-2222-2222-2222-222222222222"
				fallback={<span data-testid="fallback">F</span>}
				size={32}
			/>,
		);
		const img = screen.getByTestId("entity-logo");
		expect(img.getAttribute("src")).toContain(
			"/api/agents/22222222-2222-2222-2222-222222222222/logo",
		);
	});

	it("falls back to fallback element when the image errors (no logo set)", () => {
		render(
			<EntityLogo
				entityType="app"
				entityId="11111111-1111-1111-1111-111111111111"
				fallback={<span data-testid="fallback">F</span>}
				size={32}
			/>,
		);
		const img = screen.getByTestId("entity-logo");
		fireEvent.error(img);
		expect(screen.getByTestId("fallback")).toBeInTheDocument();
		expect(screen.queryByTestId("entity-logo")).toBeNull();
	});

	it("renders inline logo (data URL) directly without hitting the per-entity endpoint", () => {
		const dataUrl = "data:image/svg+xml;base64,PHN2Zy8+";
		render(
			<EntityLogo
				entityType="app"
				entityId="11111111-1111-1111-1111-111111111111"
				logo={dataUrl}
				fallback={<span data-testid="fallback">F</span>}
				size={32}
			/>,
		);
		const img = screen.getByTestId("entity-logo");
		expect(img.getAttribute("src")).toBe(dataUrl);
	});

	it.each(["app", "agent", "solution", "integration", "form"] as const)("replaces the %s placeholder after its logo loads", (entityType) => {
		render(
			<EntityLogo
				entityType={entityType}
				entityId="11111111-1111-1111-1111-111111111111"
				logo="/images/app-logo.png"
				fallback={<span>F</span>}
				size={32}
			/>,
		);
		const img = screen.getByRole("presentation");
		expect(img).toHaveClass("opacity-0");
		expect(screen.getByText("F")).toBeInTheDocument();
		fireEvent.load(img);
		expect(img).toHaveClass("opacity-100");
		expect(screen.queryByText("F")).not.toBeInTheDocument();
	});

	it("falls back when a list-provided logo URL fails", () => {
		render(
			<EntityLogo
				entityType="agent"
				entityId="22222222-2222-2222-2222-222222222222"
				logo="/api/agents/22222222-2222-2222-2222-222222222222/logo"
				fallback={<span data-testid="fallback">F</span>}
				size={32}
			/>,
		);
		fireEvent.error(screen.getByTestId("entity-logo"));
		expect(screen.getByTestId("fallback")).toBeInTheDocument();
	});

	it("renders fallback without making any request when logo is explicitly null", () => {
		render(
			<EntityLogo
				entityType="agent"
				entityId="22222222-2222-2222-2222-222222222222"
				logo={null}
				fallback={<span data-testid="fallback">F</span>}
				size={32}
			/>,
		);
		expect(screen.getByTestId("fallback")).toBeInTheDocument();
		expect(screen.queryByTestId("entity-logo")).toBeNull();
	});

	it("restores the placeholder while a replacement loads and when it fails", () => {
		const props = { entityType: "app" as const, entityId: "app-1", size: 32, fallback: <span>App placeholder</span> };
		const { rerender } = render(<EntityLogo {...props} logo="/first.svg" />);
		fireEvent.load(screen.getByRole("presentation"));
		expect(screen.queryByText("App placeholder")).not.toBeInTheDocument();
		rerender(<EntityLogo {...props} logo="/replacement.svg" />);
		expect(screen.getByText("App placeholder")).toBeInTheDocument();
		fireEvent.error(screen.getByRole("presentation"));
		expect(screen.getByText("App placeholder")).toBeInTheDocument();
		expect(screen.queryByRole("presentation")).not.toBeInTheDocument();
		rerender(<EntityLogo {...props} logo="/third.svg" />);
		fireEvent.load(screen.getByRole("presentation"));
		expect(screen.queryByText("App placeholder")).not.toBeInTheDocument();
		rerender(<EntityLogo {...props} logo={null} />);
		expect(screen.getByText("App placeholder")).toBeInTheDocument();
	});

	it("appends cacheKey to bust browser cache", () => {
		render(
			<EntityLogo
				entityType="app"
				entityId="11111111-1111-1111-1111-111111111111"
				fallback={<span>F</span>}
				size={32}
				cacheKey="v2"
			/>,
		);
		const img = screen.getByTestId("entity-logo");
		expect(img.getAttribute("src")).toContain("v2");
	});
});
