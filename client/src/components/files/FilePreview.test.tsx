import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/app-sdk/files", () => ({
	files: {
		read: vi.fn(),
		readBytes: vi.fn(),
		signedUrl: vi.fn(),
		download: vi.fn(),
	},
}));
import { files } from "@/lib/app-sdk/files";
import { FilePreview } from "./FilePreview";

beforeEach(() => {
	// jsdom lacks createObjectURL.
	globalThis.URL.createObjectURL = vi.fn(() => "blob:mock");
	globalThis.URL.revokeObjectURL = vi.fn();
});

describe("FilePreview", () => {
	beforeEach(() => {
		vi.mocked(files.read).mockReset();
		vi.mocked(files.readBytes).mockReset();
	});

	it("prompts to select when no path", () => {
		render(<FilePreview location="gallery" scope={null} path={null} />);
		expect(screen.getByText(/select a file/i)).toBeInTheDocument();
	});

	it("renders text content for a text file", async () => {
		vi.mocked(files.read).mockResolvedValue("hello world");
		render(
			<FilePreview location="gallery" scope={null} path="notes.txt" />,
		);
		await waitFor(() =>
			expect(screen.getByText("hello world")).toBeInTheDocument(),
		);
		expect(files.read).toHaveBeenCalledWith("notes.txt", {
			location: "gallery",
			scope: null,
		});
	});

	it("renders an image from authenticated bytes (blob url)", async () => {
		vi.mocked(files.readBytes).mockResolvedValue(new Uint8Array([1, 2, 3]));
		render(<FilePreview location="gallery" scope={null} path="pic.png" />);
		await waitFor(() => {
			const img = screen.getByRole("img");
			expect(img).toHaveAttribute("src", "blob:mock");
		});
		expect(files.readBytes).toHaveBeenCalledWith("pic.png", {
			location: "gallery",
			scope: null,
		});
	});

	it("shows a friendly error (not raw 'Forbidden') when a read fails", async () => {
		vi.mocked(files.read).mockRejectedValue(new Error("Forbidden"));
		render(
			<FilePreview location="gallery" scope={null} path="secret.txt" />,
		);
		await waitFor(() =>
			expect(
				screen.getByText(/couldn’t load this file/i),
			).toBeInTheDocument(),
		);
		expect(screen.queryByText(/^Forbidden$/)).not.toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /download instead/i }),
		).toBeInTheDocument();
	});

	it("offers download for types with no inline preview", () => {
		render(
			<FilePreview location="gallery" scope={null} path="archive.zip" />,
		);
		expect(
			screen.getByText(/no inline preview for this file type/i),
		).toBeInTheDocument();
	});
	it("retries preview and discloses truncated text", async () => {
		vi.mocked(files.read)
			.mockRejectedValueOnce(new Error("Unavailable"))
			.mockResolvedValue("a".repeat(6001));
		render(
			<FilePreview location="gallery" scope="org-1" path="notes.txt" />,
		);
		fireEvent.click(
			await screen.findByRole("button", { name: "Retry preview" }),
		);
		expect(
			await screen.findByText(/Showing the first 6,000/),
		).toBeInTheDocument();
		expect(screen.getByText("a".repeat(6000))).toBeInTheDocument();
		expect(files.read).toHaveBeenLastCalledWith("notes.txt", {
			location: "gallery",
			scope: "org-1",
		});
	});

	it("does not display a late response for a previously selected file", async () => {
		let finish!: (text: string) => void;
		vi.mocked(files.read)
			.mockReturnValueOnce(
				new Promise<string>((resolve) => {
					finish = resolve;
				}),
			)
			.mockResolvedValue("current content");
		const view = render(
			<FilePreview location="gallery" scope={null} path="old.txt" />,
		);
		view.rerender(
			<FilePreview location="gallery" scope={null} path="current.txt" />,
		);
		expect(await screen.findByText("current content")).toBeInTheDocument();
		finish("outdated content");
		await waitFor(() =>
			expect(
				screen.queryByText("outdated content"),
			).not.toBeInTheDocument(),
		);
	});

	it("recovers a failed download and revokes its object URL", async () => {
		vi.mocked(files.download)
			.mockRejectedValueOnce(new Error("Unavailable"))
			.mockResolvedValue(new Blob(["archive"]));
		const click = vi
			.spyOn(HTMLAnchorElement.prototype, "click")
			.mockImplementation(() => {});
		render(
			<FilePreview location="gallery" scope="org-1" path="archive.zip" />,
		);
		fireEvent.click(screen.getByRole("button", { name: "Download" }));
		fireEvent.click(
			await screen.findByRole("button", { name: "Retry download" }),
		);
		await waitFor(() => expect(click).toHaveBeenCalledOnce());
		expect(files.download).toHaveBeenLastCalledWith("archive.zip", {
			location: "gallery",
			scope: "org-1",
		});
		expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock");
		expect(screen.queryByRole("alert")).not.toBeInTheDocument();
		click.mockRestore();
	});

	it("handles an image that cannot be decoded and releases its URL", async () => {
		vi.mocked(files.readBytes).mockResolvedValue(new Uint8Array([1]));
		const view = render(
			<FilePreview location="gallery" scope={null} path="pic.png" />,
		);
		fireEvent.error(await screen.findByRole("img"));
		expect(
			await screen.findByRole("button", { name: "Retry preview" }),
		).toBeInTheDocument();
		view.unmount();
		expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock");
	});
});
