import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";

const mockUseOAuthRefreshJobStatus = vi.fn();
vi.mock("@/hooks/useOAuth", () => ({
	useOAuthRefreshJobStatus: () => mockUseOAuthRefreshJobStatus(),
}));

import { RefreshJobStatus } from "./RefreshJobStatus";

describe("RefreshJobStatus", () => {
	beforeEach(() => {
		mockUseOAuthRefreshJobStatus.mockReset();
	});

	it("shows loading and empty states", () => {
		mockUseOAuthRefreshJobStatus.mockReturnValue({
			data: undefined,
			isLoading: true,
		});
		renderWithProviders(<RefreshJobStatus />);
		expect(screen.getByText("Loading status...")).toBeInTheDocument();

		mockUseOAuthRefreshJobStatus.mockReturnValue({
			data: null,
			isLoading: false,
		});
		renderWithProviders(<RefreshJobStatus />);
		expect(screen.getByText("No job runs yet")).toBeInTheDocument();
		expect(
			screen.getByText(/runs every 15 minutes/i),
		).toBeInTheDocument();
	});

	it("shows an error state with a semantic danger panel", () => {
		mockUseOAuthRefreshJobStatus.mockReturnValue({
			data: {
				error: "job failed",
				updated_at: "2026-09-07T10:00:00",
				refresh_failed: 0,
				needs_refresh: 0,
				refreshed_successfully: 0,
				total_connections: 4,
			},
			isLoading: false,
		});
		renderWithProviders(<RefreshJobStatus />);
		expect(screen.getByText("Error")).toBeInTheDocument();
		expect(screen.getByText("job failed")).toBeInTheDocument();
		expect(screen.queryByRole("button", { name: /view logs/i })).not.toBeInTheDocument();
	});

	it("opens the logs dialog and shows success summary text", async () => {
		mockUseOAuthRefreshJobStatus.mockReturnValue({
			data: {
				error: null,
				updated_at: "2026-09-07T10:00:00",
				refresh_failed: 0,
				needs_refresh: 2,
				refreshed_successfully: 2,
				total_connections: 3,
				errors: [],
			},
			isLoading: false,
		});
		const { user } = renderWithProviders(<RefreshJobStatus />);
		expect(screen.getByRole("button", { name: /view logs/i })).toHaveClass(
			"min-h-11",
		);

		await user.click(screen.getByRole("button", { name: /view logs/i }));

		expect(screen.getByRole("dialog")).toBeInTheDocument();
		expect(screen.getByText("Token Refresh Job Logs")).toBeInTheDocument();
		expect(screen.getByText(/All tokens refreshed successfully!/i)).toBeInTheDocument();
		expect(screen.getByText(/Found 3 connections/i)).toBeInTheDocument();
	});
	it("distinguishes a failed read from an empty history and retries", async () => {
		const refetch = vi.fn();
		mockUseOAuthRefreshJobStatus.mockReturnValue({ data: null, isLoading: false, isError: true, isFetching: false, refetch });
		const { user } = renderWithProviders(<RefreshJobStatus />);
		expect(screen.getByRole("alert")).toHaveTextContent("Unable to load");
		expect(screen.queryByText("No job runs yet")).not.toBeInTheDocument();
		await user.click(screen.getByRole("button", {name:"Retry"}));
		expect(refetch).toHaveBeenCalledTimes(1);
	});

	it.each(["2026-09-07T10:00:00Z", "2026-09-07T10:00:00-04:00", "invalid"])("renders timestamp %s without crashing", async updated_at => {
		mockUseOAuthRefreshJobStatus.mockReturnValue({data:{updated_at, refresh_failed:0, needs_refresh:0,total_connections:2},isLoading:false});
		const { user } = renderWithProviders(<RefreshJobStatus />);
		await user.click(screen.getByRole("button", {name:/View Logs/}));
		expect(screen.getByRole("dialog")).not.toHaveTextContent("Invalid Date");
	});

});
