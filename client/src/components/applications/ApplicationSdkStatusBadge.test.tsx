import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
	ApplicationSdkStatusBadge,
	canUpdateApplicationSdk,
} from "./ApplicationSdkStatusBadge";

describe("ApplicationSdkStatusBadge", () => {
	it("labels actionable SDK drift with accessible copy", () => {
		render(<ApplicationSdkStatusBadge status="update_available" />);

		expect(
			screen.getByLabelText("SDK update available"),
		).toBeInTheDocument();
		expect(screen.getByText("SDK update available")).toBeVisible();
	});

	it("prioritizes active and failed update job states over drift", () => {
		const { rerender } = render(
			<ApplicationSdkStatusBadge
				status="update_required"
				updateState="updating"
			/>,
		);

		expect(screen.getByText("Updating SDK")).toBeVisible();

		rerender(
			<ApplicationSdkStatusBadge
				status="update_required"
				updateState="failed"
			/>,
		);

		expect(screen.getByText("SDK update failed")).toBeVisible();
	});

	it("preserves the SDK status copy when retained source cannot be used", () => {
		render(<ApplicationSdkStatusBadge status="unknown" />);

		expect(screen.getByText("SDK unknown")).toBeVisible();
		expect(screen.getByLabelText("SDK unknown")).toBeVisible();
	});

	it("omits not-applicable and default current badges in compact density", () => {
		const { container, rerender } = render(
			<ApplicationSdkStatusBadge status="not_applicable" />,
		);
		expect(container).toBeEmptyDOMElement();

		rerender(<ApplicationSdkStatusBadge status="current" />);
		expect(container).toBeEmptyDOMElement();

		rerender(
			<ApplicationSdkStatusBadge
				status="current"
				showCurrent
			/>,
		);
		expect(screen.getByText("SDK current")).toBeVisible();
	});
});

describe("canUpdateApplicationSdk", () => {
	it("allows only source-backed drift or failed retries", () => {
		expect(
			canUpdateApplicationSdk({
				sdk_status: "update_available",
				sdk_source_available: true,
			}),
		).toBe(true);
		expect(
			canUpdateApplicationSdk({
				sdk_status: "update_required",
				sdk_source_available: false,
			}),
		).toBe(false);
		expect(
			canUpdateApplicationSdk({
				sdk_status: "unknown",
				sdk_source_available: true,
			}),
		).toBe(true);
		expect(
			canUpdateApplicationSdk({
				sdk_status: "current",
				sdk_source_available: true,
			}),
		).toBe(false);
		expect(
			canUpdateApplicationSdk(
				{
					sdk_status: "current",
					sdk_source_available: false,
				},
				"failed",
			),
		).toBe(false);
		expect(
			canUpdateApplicationSdk(
				{
					sdk_status: "update_available",
					sdk_source_available: true,
				},
				"updating",
			),
		).toBe(false);
	});
});
