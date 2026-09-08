import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/pages/user-settings/BasicInfo", () => ({
	BasicInfo: () => <input aria-label="Profile draft" />,
}));
vi.mock("@/pages/user-settings/Security", () => ({
	Security: () => <button>Security settings</button>,
}));
vi.mock("@/pages/user-settings/Developer", () => ({
	DeveloperSettings: () => <button>Developer settings</button>,
}));
vi.mock("@/components/user/UserMCPConnections", () => ({
	UserMCPConnections: () => <button>Connections settings</button>,
}));
vi.mock("@/pages/user-settings/Preferences", () => ({
	Preferences: () => <button>Preference settings</button>,
}));
import { UserSettings } from "./UserSettings";

function Location() {
	return <output aria-label="Current route">{useLocation().pathname}</output>;
}

describe("account settings navigation", () => {
	it("recovers unknown tabs and preserves drafts across tab changes without exposing inactive controls", async () => {
		const user = userEvent.setup();
		render(
			<MemoryRouter initialEntries={["/user-settings/unknown"]}>
				<UserSettings />
				<Location />
			</MemoryRouter>,
		);
		await waitFor(() =>
			expect(screen.getByLabelText("Current route")).toHaveTextContent(
				"/user-settings/basic-info",
			),
		);
		await user.type(
			screen.getByRole("textbox", { name: "Profile draft" }),
			"Unsaved profile",
		);
		expect(
			screen.queryByRole("button", { name: "Developer settings" }),
		).not.toBeInTheDocument();
		await user.click(screen.getByRole("tab", { name: "Developer" }));
		expect(
			screen.queryByRole("textbox", { name: "Profile draft" }),
		).not.toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Developer settings" }),
		).toBeVisible();
		await user.click(screen.getByRole("tab", { name: "Basic Info" }));
		expect(
			screen.getByRole("textbox", { name: "Profile draft" }),
		).toHaveValue("Unsaved profile");
		expect(
			screen.queryByRole("button", { name: "Developer settings" }),
		).not.toBeInTheDocument();
	});
});
