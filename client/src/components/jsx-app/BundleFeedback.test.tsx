import { expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import {
	AutoMigrateNotice,
	BuildErrorBanner,
	BundleLoadFailure,
} from "./BundleFeedback";

it("keeps every diagnostic available and exposes separate notice dismissals", async () => {
	const buildDismiss = vi.fn(),
		migrationDismiss = vi.fn();
	const errors = Array.from({ length: 7 }, (_, index) => ({
		text: `Failure ${index + 1}`,
		file: `src/pages/view${index}.tsx`,
		line: index + 1,
		column: 3,
		line_text: null,
	}));
	const { user } = renderWithProviders(
		<>
			<BuildErrorBanner errors={errors} onDismiss={buildDismiss} />
			<AutoMigrateNotice onDismiss={migrationDismiss} />
		</>,
	);
	expect(screen.getByText("Failure 7")).toBeInTheDocument();
	await user.click(screen.getByText("Show 2 more errors"));
	expect(screen.getByText("Failure 7").closest("details")).toHaveAttribute(
		"open",
	);
	await user.click(
		screen.getByRole("button", { name: "Dismiss build errors" }),
	);
	expect(buildDismiss).toHaveBeenCalledOnce();
	expect(migrationDismiss).not.toHaveBeenCalled();
	await user.click(
		screen.getByRole("button", { name: "Dismiss runtime update notice" }),
	);
	expect(migrationDismiss).toHaveBeenCalledOnce();
});
it("preserves the full bundle error and offers reload", async () => {
	const retry = vi.fn();
	const { user } = renderWithProviders(
		<BundleLoadFailure error="Long source diagnostic" onRetry={retry} />,
	);
	expect(screen.getByLabelText("Bundle error details")).toHaveTextContent(
		"Long source diagnostic",
	);
	expect(
		screen.getByLabelText("Bundle error details").closest("details"),
	).not.toHaveAttribute("open");
	await user.click(screen.getByText("Technical details"));
	expect(
		screen.getByLabelText("Bundle error details").closest("details"),
	).toHaveAttribute("open");
	await user.click(screen.getByRole("button", { name: "Reload app" }));
	expect(retry).toHaveBeenCalledOnce();
});
