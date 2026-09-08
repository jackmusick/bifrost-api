import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getSettings = vi.fn();
const updateSettings = vi.fn();
const cleanup = vi.fn();

vi.mock("@/services/artifactRetention", () => ({
	getArtifactRetentionSettings: () => getSettings(),
	updateArtifactRetentionSettings: (settings: unknown) =>
		updateSettings(settings),
	cleanupExpiredArtifacts: () => cleanup(),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import { ArtifactRetentionSettings } from "./ArtifactRetentionSettings";

describe("ArtifactRetentionSettings", () => {
	beforeEach(() => {
		getSettings.mockReset().mockResolvedValue({
			enabled: false,
			retention_days: 90,
		});
		updateSettings
			.mockReset()
			.mockImplementation((settings) => Promise.resolve(settings));
		cleanup.mockReset().mockResolvedValue({
			job_id: "job-1",
			status: "queued",
			reused: false,
			notification_id: "notification-1",
		});
	});

	it("lets a platform administrator enable scheduled cleanup", async () => {
		const user = userEvent.setup();
		render(<ArtifactRetentionSettings />);

		const toggle = await screen.findByRole("switch", {
			name: "Enable Scheduled Cleanup",
		});
		await waitFor(() => expect(toggle).toBeEnabled());
		await user.click(toggle);

		await waitFor(() =>
			expect(updateSettings).toHaveBeenCalledWith({
				enabled: true,
				retention_days: 90,
			}),
		);
	});

	it("saves retention days and runs cleanup", async () => {
		const user = userEvent.setup();
		render(<ArtifactRetentionSettings />);

		const days = await screen.findByLabelText("Retention Days");
		await waitFor(() => expect(days).toBeEnabled());
		fireEvent.change(days, { target: { value: "30" } });
		fireEvent.blur(days);
		await waitFor(() =>
			expect(updateSettings).toHaveBeenCalledWith({
				enabled: false,
				retention_days: 30,
			}),
		);
		await user.click(screen.getByRole("button", { name: "Run Cleanup" }));
		expect(cleanup).toHaveBeenCalledOnce();
	});
	it("keeps unavailable settings disabled until a successful retry", async () => {
		getSettings.mockRejectedValueOnce(new Error("Offline"));
		const user = userEvent.setup();
		render(<ArtifactRetentionSettings />);
		await screen.findByRole("alert");
		expect(
			screen.getByRole("switch", { name: "Enable Scheduled Cleanup" }),
		).toBeDisabled();
		expect(
			screen.getByRole("button", { name: "Run Cleanup" }),
		).toBeDisabled();
		expect(screen.getByLabelText("Retention Days")).toBeDisabled();
		await user.click(screen.getByRole("button", { name: "Retry" }));
		await waitFor(() =>
			expect(
				screen.getByRole("switch", {
					name: "Enable Scheduled Cleanup",
				}),
			).toBeEnabled(),
		);
		expect(updateSettings).not.toHaveBeenCalled();
	});
	it("allows clearing and typing a new value without replacing the empty draft", async () => {
		const user = userEvent.setup();
		render(<ArtifactRetentionSettings />);
		const days = screen.getByLabelText("Retention Days");
		await waitFor(() => expect(days).toBeEnabled());
		await user.clear(days);
		expect(days).toHaveValue(null);
		await user.tab();
		expect(await screen.findByRole("alert")).toHaveTextContent(
			"Enter a number",
		);
		expect(updateSettings).not.toHaveBeenCalled();
		expect(
			screen.getByRole("button", { name: "Run Cleanup" }),
		).toBeDisabled();
		await user.type(days, "30");
		await user.tab();
		await waitFor(() =>
			expect(updateSettings).toHaveBeenCalledWith({
				enabled: false,
				retention_days: 30,
			}),
		);
	});
	it("retains failed settings and separately retries cleanup failure", async () => {
		updateSettings.mockRejectedValueOnce(new Error("Offline"));
		cleanup.mockRejectedValueOnce(new Error("Offline"));
		const user = userEvent.setup();
		render(<ArtifactRetentionSettings />);
		const days = screen.getByLabelText("Retention Days");
		await waitFor(() => expect(days).toBeEnabled());
		fireEvent.change(days, { target: { value: "30" } });
		fireEvent.blur(days);
		await screen.findByRole("button", { name: "Retry save" });
		expect(days).toHaveValue(30);
		expect(
			screen.getByRole("button", { name: "Run Cleanup" }),
		).toBeDisabled();
		await user.click(screen.getByRole("button", { name: "Retry save" }));
		await waitFor(() =>
			expect(
				screen.getByRole("button", { name: "Run Cleanup" }),
			).toBeEnabled(),
		);
		await user.click(screen.getByRole("button", { name: "Run Cleanup" }));
		await user.click(
			await screen.findByRole("button", { name: "Retry Cleanup" }),
		);
		await waitFor(() => expect(cleanup).toHaveBeenCalledTimes(2));
	});
});
