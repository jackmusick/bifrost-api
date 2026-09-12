import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { listShares } from "@/services/fileStructure";
import { SharesOverview } from "./SharesOverview";

vi.mock("@/services/fileStructure", () => ({ listShares: vi.fn() }));
function setup(readOnly = false) {
	const onSelect = vi.fn();
	render(
		<QueryClientProvider
			client={
				new QueryClient({
					defaultOptions: { queries: { retry: false } },
				})
			}
		>
			<SharesOverview
				scope="global"
				readOnly={readOnly}
				onSelect={onSelect}
			/>
		</QueryClientProvider>,
	);
	return onSelect;
}
describe("SharesOverview", () => {
	beforeEach(() => vi.resetAllMocks());
	it("opens the selected share and labels its policy and read-only state", async () => {
		vi.mocked(listShares).mockResolvedValue([
			{ location: "Customer files", readOnly: true, hasPolicy: true },
		]);
		const onSelect = setup();
		await userEvent
			.setup()
			.click(
				await screen.findByRole("button", { name: /Customer files/ }),
			);
		expect(onSelect).toHaveBeenCalledWith("Customer files", "");
		expect(screen.getByText("Read only")).toBeInTheDocument();
		expect(screen.getByText("Policy configured")).toBeInTheDocument();
		expect(screen.getByText("1 share")).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /Customer files/ }),
		).toHaveClass("w-full");
		expect(screen.getByRole("list")).toHaveClass("overflow-auto");
		expect(screen.getByRole("list")).not.toHaveClass("border");
		expect(listShares).toHaveBeenCalledWith("global");
	});
	it("shows a solution-specific empty state", async () => {
		vi.mocked(listShares).mockResolvedValue([]);
		setup(true);
		expect(
			await screen.findByText("This solution has no file shares."),
		).toBeInTheDocument();
	});
	it("recovers a failed read when retry is requested", async () => {
		vi.mocked(listShares)
			.mockRejectedValueOnce(new Error("Unavailable"))
			.mockResolvedValue([
				{ location: "Recovered", readOnly: false, hasPolicy: false },
			]);
		setup();
		await userEvent
			.setup()
			.click(await screen.findByRole("button", { name: "Retry shares" }));
		expect(
			await screen.findByRole("button", { name: /Recovered/ }),
		).toBeInTheDocument();
	});
});
