import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { ReportRecordList } from "./ReportRecordList";

describe("ReportRecordList", () => {
	it("renders records as card-like rows and exposes the sort controls", async () => {
		const onSort = vi.fn();
		const { user } = renderWithProviders(
			<ReportRecordList
				label="workflow usage"
				sort={{ by: "name", dir: "asc" }}
				onSort={onSort}
				columns={[
					{ key: "name", label: "Workflow" },
					{ key: "runs", label: "Runs" },
				]}
				records={[
					{
						id: "row-1",
						title: "Alpha workflow",
						metrics: [
							{ label: "Runs", value: "12" },
							{ label: "Cost", value: "$3.50", fullWidth: true },
						],
					},
				]}
			/>,
		);

		const section = screen.getByRole("region", {
			name: /workflow usage/i,
		});
		expect(section).toBeInTheDocument();
		expect(screen.getByText("Alpha workflow")).toBeInTheDocument();
		expect(screen.getByText("Runs")).toBeInTheDocument();
		expect(screen.getByText("$3.50")).toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: /sort descending/i }));
		expect(onSort).toHaveBeenCalledWith("name");
	});
});
