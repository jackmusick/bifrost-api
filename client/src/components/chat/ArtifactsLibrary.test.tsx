import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test-utils";

const services = vi.hoisted(() => ({
	listChatArtifacts: vi.fn(),
	renameChatArtifact: vi.fn(),
	deleteChatArtifact: vi.fn(),
}));

vi.mock("@/services/chatAttachments", async () => {
	const actual = await vi.importActual<typeof import("@/services/chatAttachments")>(
		"@/services/chatAttachments",
	);
	return { ...actual, ...services };
});

vi.mock("./FilePreviewSheet", () => ({
	FilePreviewSheet: ({ attachment }: { attachment: { filename: string } | null }) =>
		attachment ? <div data-testid="file-preview">{attachment.filename}</div> : null,
}));

import { ArtifactsLibrary } from "./ArtifactsLibrary";

const artifacts = [
	{
		id: "generated-1",
		conversation_id: "conversation-1",
		message_id: "message-1",
		filename: "Welcome Page.html",
		content_type: "text/html",
		size_bytes: 1024,
		kind: "artifact" as const,
		conversation_title: "Welcome work",
		created_at: "2026-08-15T00:00:00Z",
	},
	{
		id: "uploaded-1",
		conversation_id: "conversation-2",
		message_id: "message-2",
		filename: "Source Notes.txt",
		content_type: "text/plain",
		size_bytes: 50,
		kind: "attachment" as const,
		conversation_title: "Research",
		created_at: "2026-08-14T00:00:00Z",
	},
];

describe("ArtifactsLibrary", () => {
	beforeEach(() => {
		services.listChatArtifacts.mockReset();
		services.listChatArtifacts.mockResolvedValue(artifacts);
	});

	it("shows durable chat files and previews the selected artifact", async () => {
		const { user } = renderWithProviders(<ArtifactsLibrary />);

		expect(await screen.findByText("Welcome Page.html")).toBeInTheDocument();
		expect(screen.getByText("Source Notes.txt")).toBeInTheDocument();
		await user.click(
			screen.getByRole("button", { name: "Preview Welcome Page.html" }),
		);
		expect(screen.getByTestId("file-preview")).toHaveTextContent("Welcome Page.html");
	});

	it("filters the library by origin", async () => {
		const { user } = renderWithProviders(<ArtifactsLibrary />);
		await screen.findByText("Welcome Page.html");

		const uploadedFilter = screen.getByRole("button", { name: "Uploaded" });
		expect(uploadedFilter).toHaveAttribute("aria-pressed", "false");
		await user.click(uploadedFilter);
		expect(uploadedFilter).toHaveAttribute("aria-pressed", "true");
		await waitFor(() =>
			expect(screen.queryByText("Welcome Page.html")).not.toBeInTheDocument(),
		);
		expect(screen.getByText("Source Notes.txt")).toBeInTheDocument();
	});

	it("renames an artifact with Enter and returns focus to the manage trigger", async () => {
		services.renameChatArtifact.mockResolvedValueOnce({
			...artifacts[0],
			filename: "Renamed Page.html",
		});

		const { user } = renderWithProviders(<ArtifactsLibrary />);
		await screen.findByText("Welcome Page.html");

		await user.click(
			screen.getByRole("button", { name: "Manage Welcome Page.html" }),
		);
		await user.click(screen.getByRole("menuitem", { name: "Rename" }));

		const input = screen.getByRole("textbox", { name: "Filename" });
		await user.clear(input);
		await user.type(input, "Renamed Page.html{Enter}");

		await waitFor(() =>
			expect(services.renameChatArtifact).toHaveBeenCalledWith(
				"generated-1",
				"Renamed Page.html",
			),
		);
		await waitFor(() =>
			expect(screen.getByText("Renamed Page.html")).toBeInTheDocument(),
		);
		expect(
			screen.getByRole("button", { name: "Manage Renamed Page.html" }),
		).toHaveFocus();
	});

	it("deletes an artifact and returns focus to the heading fallback", async () => {
		services.deleteChatArtifact.mockResolvedValueOnce(undefined);

		const { user } = renderWithProviders(<ArtifactsLibrary />);
		await screen.findByText("Welcome Page.html");

		await user.click(
			screen.getByRole("button", { name: "Manage Welcome Page.html" }),
		);
		await user.click(screen.getByRole("menuitem", { name: "Delete" }));
		await user.click(screen.getByRole("button", { name: /^delete$/i }));

		await waitFor(() =>
			expect(screen.queryByText("Welcome Page.html")).not.toBeInTheDocument(),
		);
		expect(screen.getByRole("heading", { name: "Artifacts" })).toHaveFocus();
	});
});
