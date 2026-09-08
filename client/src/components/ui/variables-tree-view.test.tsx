import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VariablesTreeView } from "./variables-tree-view";
import { copyToClipboard } from "@/lib/clipboard";
import { toast } from "sonner";

vi.mock("@/lib/clipboard", () => ({ copyToClipboard: vi.fn() }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

beforeEach(() => vi.clearAllMocks());

describe("VariablesTreeView", () => {
	it("supports keyboard inspection of nested arrays and empty objects", async () => {
		const user = userEvent.setup();
		render(
			<VariablesTreeView
				data={{
					result: {
						records: [{ message: "Complete message" }],
						empty: {},
					},
				}}
			/>,
		);
		const result = screen.getByRole("button", { name: "Expand result" });
		result.focus();
		await user.keyboard("{Enter}");
		expect(result).toHaveAttribute("aria-expanded", "true");
		await user.click(
			screen.getByRole("button", { name: "Expand records" }),
		);
		await user.click(screen.getByRole("button", { name: "Expand [0]" }));
		expect(screen.getByText('"Complete message"')).toBeVisible();
		await user.click(screen.getByRole("button", { name: "Expand empty" }));
		expect(screen.getByText("Empty object")).toBeVisible();
		result.focus();
		await user.keyboard(" ");
		expect(
			screen.queryByText('"Complete message"'),
		).not.toBeInTheDocument();
	});

	it("copies raw primitives and complete nested JSON without mouse hover", async () => {
		vi.mocked(copyToClipboard).mockResolvedValue(true);
		const user = userEvent.setup();
		const data = {
			message: "first line\nsecond line",
			nested: { value: false },
			missing: undefined,
		};
		render(<VariablesTreeView data={data} />);
		await user.click(
			screen.getByRole("button", { name: "Copy message value" }),
		);
		expect(copyToClipboard).toHaveBeenLastCalledWith(data.message);
		await user.click(
			screen.getByRole("button", { name: "Copy nested value" }),
		);
		expect(copyToClipboard).toHaveBeenLastCalledWith(
			JSON.stringify(data.nested, null, 2),
		);
		await user.click(
			screen.getByRole("button", { name: "Copy missing value" }),
		);
		expect(copyToClipboard).toHaveBeenLastCalledWith("undefined");
	});

	it("keeps copy available for retry after clipboard failure", async () => {
		vi.mocked(copyToClipboard)
			.mockResolvedValueOnce(false)
			.mockResolvedValueOnce(true);
		const user = userEvent.setup();
		render(<VariablesTreeView data={{ value: "Retained" }} />);
		const copy = screen.getByRole("button", { name: "Copy value value" });
		await user.click(copy);
		expect(toast.error).toHaveBeenCalledWith("Failed to copy to clipboard");
		expect(copy).toBeEnabled();
		await user.click(copy);
		expect(copyToClipboard).toHaveBeenCalledTimes(2);
		expect(toast.success).toHaveBeenCalled();
	});
});
