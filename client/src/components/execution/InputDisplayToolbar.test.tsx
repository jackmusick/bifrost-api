import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { InputDisplayToolbar } from "./InputDisplayToolbar";
import { copyToClipboard } from "@/lib/clipboard";
vi.mock("@/lib/clipboard", () => ({ copyToClipboard: vi.fn() }));

describe("InputDisplayToolbar", () => {
	it("copies the full payload and supports retry after failure in pretty view", async () => {
		const user = userEvent.setup();
		vi.mocked(copyToClipboard)
			.mockResolvedValueOnce(false)
			.mockResolvedValueOnce(true);
		const data = { message: "x".repeat(30000) };
		render(
			<InputDisplayToolbar
				inputData={data}
				view="pretty"
				showToggle
				onViewChange={vi.fn()}
			/>,
		);
		await user.click(
			screen.getByRole("button", { name: "Copy" }),
		);
		expect(screen.getByRole("status")).toHaveTextContent("Couldn’t copy");
		await user.click(screen.getByRole("button", { name: "Retry copy" }));
		expect(copyToClipboard).toHaveBeenLastCalledWith(
			JSON.stringify(data, null, 2),
		);
		expect(screen.getByRole("status")).toHaveTextContent(
			"All data copied",
		);
	});

	it("does not report an old pending copy as success for replacement input", async () => {
		const user = userEvent.setup();
		let resolve!: (success: boolean) => void;
		vi.mocked(copyToClipboard).mockReturnValueOnce(
			new Promise((done) => {
				resolve = done;
			}),
		);
		const props = {
			view: "pretty" as const,
			showToggle: true,
			onViewChange: vi.fn(),
		};
		const { rerender } = render(
			<InputDisplayToolbar {...props} inputData={{ id: "old" }} />,
		);
		await user.click(
			screen.getByRole("button", { name: "Copy" }),
		);
		expect(screen.getByRole("button", { name: "Copying…" })).toBeDisabled();
		rerender(<InputDisplayToolbar {...props} inputData={{ id: "new" }} />);
		resolve(true);
		await waitFor(() =>
			expect(
				screen.getByRole("button", { name: "Copy" }),
			).toBeEnabled(),
		);
		expect(screen.queryByRole("status")).not.toBeInTheDocument();
	});
});
