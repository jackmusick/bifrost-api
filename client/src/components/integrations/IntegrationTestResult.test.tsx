import { expect, it } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { IntegrationTestResult } from "./IntegrationTestResult";

it("announces success and retains a zero duration", () => {
	renderWithProviders(
		<IntegrationTestResult
			result={{ success: true, message: "Connected", duration_ms: 0 }}
		/>,
	);
	expect(screen.getByRole("status")).toHaveTextContent("Duration: 0 ms");
});
it("announces failure and exposes complete error details", () => {
	renderWithProviders(
		<IntegrationTestResult
			result={{
				success: false,
				message: "Rejected",
				error_details: "The provider rejected the requested scope.",
			}}
		/>,
	);
	expect(screen.getByRole("alert")).toHaveTextContent(
		"The provider rejected the requested scope.",
	);
});
