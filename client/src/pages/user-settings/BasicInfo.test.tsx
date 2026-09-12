import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, it, expect, vi } from "vitest";
const service = vi.hoisted(() => ({
	getProfile: vi.fn(),
	updateProfile: vi.fn(),
	changePassword: vi.fn(),
}));
vi.mock("@/services/profile", () => ({ profileService: service }));
vi.mock("@/contexts/AuthContext", () => ({
	useAuth: () => ({ user: { email: "fixture@example.test" } }),
}));
vi.mock("@/components/LogoDropZone", () => ({ LogoDropZone: () => null }));
import { BasicInfo } from "./BasicInfo";
const profile = {
	id: "fixture",
	email: "fixture@example.test",
	name: "Fixture",
	has_password: false,
	has_avatar: false,
	organization_id: null,
	is_superuser: false,
};
beforeEach(() => {
	vi.clearAllMocks();
	service.getProfile.mockResolvedValue(profile);
	service.updateProfile.mockResolvedValue({ ...profile, name: "Updated" });
	service.changePassword.mockResolvedValue(undefined);
});
it("retries initial loading and retains the name after a failed save", async () => {
	service.getProfile.mockRejectedValueOnce(new Error("Offline"));
	service.updateProfile.mockRejectedValueOnce(new Error("Offline"));
	const user = userEvent.setup();
	render(<BasicInfo />);
	await user.click(await screen.findByRole("button", { name: "Retry" }));
	const name = await screen.findByLabelText("Name");
	await user.clear(name);
	await user.type(name, "Updated");
	await user.click(screen.getByRole("button", { name: "Save Changes" }));
	await user.click(await screen.findByRole("button", { name: "Retry save" }));
	await waitFor(() =>
		expect(screen.getByRole("button", { name: "Saved" })).toBeDisabled(),
	);
	expect(name).toHaveValue("Updated");
});
it("retains failed password input and completes setting a password without a second profile fetch", async () => {
	service.changePassword.mockRejectedValueOnce(
		new Error("Synthetic rejection"),
	);
	const user = userEvent.setup();
	render(<BasicInfo />);
	const password = await screen.findByLabelText("Password", {
		selector: "input",
	});
	const confirm = screen.getByLabelText("Confirm Password", {
		selector: "input",
	});
	await user.type(password, "synthetic-example");
	await user.type(confirm, "synthetic-example");
	await user.click(screen.getByRole("button", { name: "Show password" }));
	expect(password).toHaveAttribute("type", "text");
	await user.click(screen.getByRole("button", { name: "Hide password" }));
	await user.click(screen.getByRole("button", { name: "Set Password" }));
	await screen.findByText("Synthetic rejection");
	expect(password).toHaveValue("synthetic-example");
	await user.click(screen.getByRole("button", { name: "Set Password" }));
	await screen.findByLabelText("Current Password", { selector: "input" });
	expect(password).toHaveValue("");
	expect(service.getProfile).toHaveBeenCalledTimes(1);
});

it("validates matching passwords and preserves the existing-password contract", async () => {
	service.getProfile.mockResolvedValue({ ...profile, has_password: true });
	const user = userEvent.setup();
	render(<BasicInfo />);
	await user.type(
		await screen.findByLabelText("Current Password", { selector: "input" }),
		"synthetic-current",
	);
	await user.type(
		screen.getByLabelText("New Password", { selector: "input" }),
		"synthetic-next",
	);
	await user.type(
		screen.getByLabelText("Confirm Password", { selector: "input" }),
		"different-value",
	);
	await user.click(screen.getByRole("button", { name: "Change Password" }));
	expect(screen.getByText("Passwords do not match")).toBeVisible();
	expect(service.changePassword).not.toHaveBeenCalled();
	await user.clear(
		screen.getByLabelText("Confirm Password", { selector: "input" }),
	);
	await user.type(
		screen.getByLabelText("Confirm Password", { selector: "input" }),
		"synthetic-next",
	);
	await user.click(screen.getByRole("button", { name: "Change Password" }));
	await waitFor(() =>
		expect(service.changePassword).toHaveBeenCalledWith(
			"synthetic-current",
			"synthetic-next",
		),
	);
});
