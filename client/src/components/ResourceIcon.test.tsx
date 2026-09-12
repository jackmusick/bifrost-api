import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResourceIcon } from "./ResourceIcon";

describe("ResourceIcon", () => {
	it("renders the card fallback at the standard feature-icon size", () => {
		render(<ResourceIcon kind="form" aria-label="Form icon" />);

		const icon = screen.getByLabelText("Form icon");
		expect(icon).toHaveClass("size-12");
	});

	it("renders uploaded integration logos with the compact table size", () => {
		render(
			<ResourceIcon
				kind="integration"
				id="integration-1"
				logo="/api/integrations/integration-1/logo?v=abc"
				size="table"
				aria-label="Integration icon"
			/>,
		);

		const icon = screen.getByLabelText("Integration icon");
		const image = screen.getByTestId("entity-logo");
		expect(icon).toHaveStyle({ width: "32px", height: "32px" });
		expect(image).toHaveAttribute(
			"src",
			"/api/integrations/integration-1/logo?v=abc",
		);
		expect(image).toHaveClass("object-contain");
	});

	it("renders uploaded form logos through the shared logo endpoint", () => {
		render(
			<ResourceIcon
				kind="form"
				id="form-1"
				logo="/api/forms/form-1/logo?v=abc"
				size="card"
				aria-label="Form logo"
			/>,
		);

		expect(screen.getByLabelText("Form logo")).toHaveStyle({
			width: "48px",
			height: "48px",
		});
		expect(screen.getByTestId("entity-logo")).toHaveAttribute(
			"src",
			"/api/forms/form-1/logo?v=abc",
		);
	});

	it("keeps decorative icons hidden by default", () => {
		const { container } = render(<ResourceIcon kind="agent" id="agent-1" />);

		expect(container.firstElementChild).toHaveAttribute(
			"aria-hidden",
			"true",
		);
	});
});
