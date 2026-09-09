import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { IntegrationConnectionStatus } from "./IntegrationList";
import type { Integration } from "@/services/integrations";
const integration = {
	id: "review",
	name: "Review",
	has_oauth_config: true,
	is_deleted: false,
	created_at: "",
	updated_at: "",
} as Integration;
describe("Integration connection status", () => {
	it("distinguishes authorized and failed connections in the same integration", () => {
		render(
			<IntegrationConnectionStatus
				integration={{
					...integration,
					connected_count: 3,
					needs_reconnection_count: 1,
				}}
			/>,
		);
		expect(screen.getByText("3 connected")).toBeInTheDocument();
		expect(screen.getByText("1 needs reconnection")).toBeInTheDocument();
	});
	it("does not imply connectivity from OAuth configuration alone", () => {
		render(
			<IntegrationConnectionStatus
				integration={{
					...integration,
					connected_count: 0,
					needs_reconnection_count: 0,
				}}
			/>,
		);
		expect(screen.getByText("Not connected")).toBeInTheDocument();
	});
	it("does not claim API key integrations are monitored", () => {
		render(
			<IntegrationConnectionStatus
				integration={{ ...integration, has_oauth_config: false }}
			/>,
		);
		expect(screen.getByText("Not monitored")).toBeInTheDocument();
	});
});
