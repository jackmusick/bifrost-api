import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/services/filePolicies", () => ({ saveFilePolicy: vi.fn() }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
import { saveFilePolicy } from "@/services/filePolicies";
import { NewShareDialog } from "./NewShareDialog";

describe("NewShareDialog", () => {
	beforeEach(() => vi.mocked(saveFilePolicy).mockReset());

	it("rejects a reserved name without calling the API", async () => {
		render(
			<NewShareDialog
				open
				onOpenChange={vi.fn()}
				scope={null}
				onCreated={vi.fn()}
			/>,
		);
		fireEvent.change(screen.getByLabelText(/share name/i), {
			target: { value: "uploads" },
		});
		fireEvent.click(screen.getByRole("button", { name: /create share/i }));
		expect(await screen.findByText(/reserved name/i)).toBeInTheDocument();
		expect(saveFilePolicy).not.toHaveBeenCalled();
	});

	it("creates the first policy (empty doc) and reports the new share", async () => {
		vi.mocked(saveFilePolicy).mockResolvedValue({
			id: "p1",
			location: "gallery",
			path: "",
			organizationId: "org-1",
			policies: { policies: [] },
		});
		const onCreated = vi.fn();
		render(
			<NewShareDialog
				open
				onOpenChange={vi.fn()}
				scope="org-1"
				onCreated={onCreated}
			/>,
		);
		fireEvent.change(screen.getByLabelText(/share name/i), {
			target: { value: "gallery" },
		});
		fireEvent.click(screen.getByRole("button", { name: /create share/i }));
		await waitFor(() =>
			expect(saveFilePolicy).toHaveBeenCalledWith({
				location: "gallery",
				path: "",
				organizationId: "org-1",
				policies: { policies: [] },
			}),
		);
		expect(onCreated).toHaveBeenCalledWith("gallery");
	});
	it("retains a failed draft, prevents pending dismissal, and retries the same request", async () => {
		let reject!: (error: Error) => void;
		vi.mocked(saveFilePolicy).mockReturnValueOnce(
			new Promise((_, fail) => {
				reject = fail;
			}),
		);
		const onOpenChange = vi.fn();
		render(
			<NewShareDialog
				open
				onOpenChange={onOpenChange}
				scope="org-1"
				onCreated={vi.fn()}
			/>,
		);
		const input = screen.getByLabelText("Share name");
		fireEvent.change(input, { target: { value: "reports" } });
		fireEvent.submit(input.closest("form")!);
		expect(input).toBeDisabled();
		expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
		fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
		expect(onOpenChange).not.toHaveBeenCalled();
		reject(new Error("Try again later"));
		expect(await screen.findByRole("alert")).toHaveTextContent(
			"Try again later",
		);
		expect(input).toHaveValue("reports");
		vi.mocked(saveFilePolicy).mockResolvedValue({
			location: "reports",
			path: "",
			policies: { policies: [] },
		});
		fireEvent.submit(input.closest("form")!);
		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		expect(vi.mocked(saveFilePolicy).mock.calls[1]).toEqual(
			vi.mocked(saveFilePolicy).mock.calls[0],
		);
	});

	it("starts a fresh draft after close or scope change", () => {
		const props = {
			open: true,
			scope: "org-1",
			onOpenChange: vi.fn(),
			onCreated: vi.fn(),
		};
		const view = render(<NewShareDialog {...props} />);
		fireEvent.change(screen.getByLabelText("Share name"), {
			target: { value: "cancelled" },
		});
		view.rerender(<NewShareDialog {...props} open={false} />);
		view.rerender(<NewShareDialog {...props} />);
		expect(screen.getByLabelText("Share name")).toHaveValue("");
		fireEvent.change(screen.getByLabelText("Share name"), {
			target: { value: "previous-scope" },
		});
		view.rerender(<NewShareDialog {...props} scope="org-2" />);
		expect(screen.getByLabelText("Share name")).toHaveValue("");
	});
});
