import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { PackageInstallForm } from "./PackageInstallForm";
import { InstalledPackageList } from "./InstalledPackageList";

it("submits from the version field and disables both install paths during installation", async () => {
	const user = userEvent.setup();
	const props = {
		packageName: "requests",
		version: "2.31.0",
		isInstalling: false,
		onPackageNameChange: vi.fn(),
		onVersionChange: vi.fn(),
		onInstall: vi.fn(),
		onInstallRequirements: vi.fn(),
	};
	const { rerender } = render(<PackageInstallForm {...props} />);
	await user.click(screen.getByLabelText("Version (optional)"));
	await user.keyboard("{Enter}");
	expect(props.onInstall).toHaveBeenCalledTimes(1);
	rerender(<PackageInstallForm {...props} isInstalling />);
	expect(
		screen.getByRole("button", { name: "Install package" }),
	).toBeDisabled();
	expect(
		screen.getByRole("button", { name: "Install requirements.txt" }),
	).toBeDisabled();
	expect(screen.getByRole("status")).toHaveTextContent(
		"Follow progress in Output",
	);
});

it("retains known packages on failure and distinguishes retry from an empty list", async () => {
	const user = userEvent.setup();
	const onRetry = vi.fn();
	const props = {
		packages: [{ name: "requests", version: "2.31.0" }],
		updates: [],
		isLoading: false,
		error: "Couldn’t load installed packages. Try again.",
		onRetry,
	};
	const { rerender } = render(<InstalledPackageList {...props} />);
	expect(screen.getByText("requests")).toBeVisible();
	expect(screen.getByRole("alert")).toHaveTextContent("Couldn’t load");
	expect(screen.queryByText(/No packages installed/)).not.toBeInTheDocument();
	await user.click(
		screen.getByRole("button", { name: "Retry loading packages" }),
	);
	expect(onRetry).toHaveBeenCalledTimes(1);
	rerender(<InstalledPackageList {...props} packages={[]} />);
	expect(screen.queryByText(/No packages installed/)).not.toBeInTheDocument();
	rerender(<InstalledPackageList {...props} packages={[]} error={null} />);
	expect(screen.getByText(/No packages installed/)).toBeVisible();
});
