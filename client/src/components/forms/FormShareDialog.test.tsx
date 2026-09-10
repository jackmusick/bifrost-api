import { act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test-utils";

const mockAuthFetch = vi.fn();
vi.mock("@/lib/api-client", () => ({
	$api: { useQuery: vi.fn(), useMutation: vi.fn() },
	authFetch: (...args: unknown[]) => mockAuthFetch(...args),
}));

vi.mock("sonner", () => ({
	toast: { error: vi.fn(), success: vi.fn() },
}));
vi.mock("react-syntax-highlighter", () => ({
	Prism: ({ children }: { children: string }) => <pre>{children}</pre>,
}));
vi.mock("react-syntax-highlighter/dist/esm/styles/prism", () => ({
	oneDark: {},
}));
vi.mock("@/components/ui/tiptap-editor", () => ({
	TiptapEditor: ({
		content,
		onChange,
		ariaLabel,
	}: {
		content: string;
		onChange?: (value: string) => void;
		ariaLabel?: string;
	}) => (
		<textarea
			aria-label={ariaLabel}
			value={content}
			onChange={(event) => onChange?.(event.target.value)}
		/>
	),
}));

import { FormShareDialog } from "./FormShareDialog";

function jsonResponse(body: unknown, ok = true) {
	return {
		ok,
		status: ok ? 200 : 400,
		json: async () => body,
		text: async () => JSON.stringify(body),
	} as unknown as Response;
}

const review = {
	fingerprint: "sha256:reviewed",
	blockers: [],
	warnings: [],
	submission_workflow: { ref: "submit.py::submit", name: "Submit request" },
	startup_workflow: null,
	provider_fields: [
		{
			field_name: "company",
			provider_ref: "providers.py::companies",
			provider_name: "Companies",
		},
	],
	file_fields: [],
};

const unpublished = {
	form_id: "form-1",
	status: "unpublished",
	public_key: null,
	allowed_origins: [],
	spam_protection_enabled: true,
	approved_fingerprint: null,
	current_fingerprint: "sha256:reviewed",
	iframe_path: null,
	warnings: [],
	blockers: [],
};

const form = {
	id: "form-1",
	name: "Customer intake",
	confirmation_markdown: "## Form submitted\n\nThank you!",
};

beforeEach(() => {
	mockAuthFetch.mockReset();
});

describe("FormShareDialog", () => {
	it("shows the private link before publishing", async () => {
		mockAuthFetch
			.mockResolvedValueOnce(jsonResponse(unpublished))
			.mockResolvedValueOnce(jsonResponse(review))
			.mockResolvedValueOnce(jsonResponse(form));

		const { user } = renderWithProviders(
			<FormShareDialog
				formId="form-1"
				formName="Customer intake"
				open
				onOpenChange={vi.fn()}
			/>,
		);

		expect(await screen.findByLabelText("Private form link")).toHaveValue(
			"http://localhost:3000/execute/form-1",
		);
		expect(
			screen.queryByLabelText("Allowed Website Origins"),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("heading", { name: "Confirmation Message" }),
		).not.toBeInTheDocument();
		await user.click(
			screen.getByRole("button", { name: "Copy private link" }),
		);
		expect(await navigator.clipboard.readText()).toBe(
			"http://localhost:3000/execute/form-1",
		);
	});

	it("requires capability confirmation before publishing", async () => {
		mockAuthFetch
			.mockResolvedValueOnce(jsonResponse(unpublished))
			.mockResolvedValueOnce(jsonResponse(review))
			.mockResolvedValueOnce(jsonResponse(form))
			.mockResolvedValueOnce(jsonResponse({ ok: true }))
			.mockResolvedValueOnce(
				jsonResponse({
					...unpublished,
					status: "published",
					public_key: "public-key",
					allowed_origins: ["https://example.com"],
					approved_fingerprint: "sha256:reviewed",
					iframe_path: "/embed/forms/public/public-key",
				}),
			)
			.mockResolvedValueOnce(jsonResponse(review))
			.mockResolvedValueOnce(jsonResponse(form));

		const { user } = renderWithProviders(
			<FormShareDialog
				formId="form-1"
				formName="Customer intake"
				open
				onOpenChange={vi.fn()}
			/>,
		);

		await screen.findByLabelText("Private form link");
		await user.click(screen.getByRole("tab", { name: "Website Embed" }));
		await user.click(
			screen.getByRole("button", { name: /Website Restrictions/ }),
		);
		await user.click(screen.getByLabelText("Allowed Website Origins"));
		await user.paste("https://example.com");
		await user.click(screen.getByRole("switch", { name: "Not Published" }));

		expect(
			screen.getByRole("heading", {
				name: "Allow anonymous form access?",
			}),
		).toBeInTheDocument();
		expect(screen.getByText(/execute submit request/i)).toBeInTheDocument();
		expect(
			screen.getByText(/query 1 approved data provider/i),
		).toHaveTextContent("Companies");
		expect(
			screen.getByText(
				/no other workflows or bifrost execution apis are granted/i,
			),
		).toBeInTheDocument();

		await user.click(
			screen.getByRole("button", { name: "Publish public embed" }),
		);

		await waitFor(() => {
			expect(mockAuthFetch).toHaveBeenCalledWith(
				"/api/forms/form-1/publication",
				expect.objectContaining({
					method: "PUT",
					body: JSON.stringify({
						reviewed_fingerprint: "sha256:reviewed",
						allowed_origins: ["https://example.com"],
						spam_protection_enabled: true,
					}),
				}),
			);
		});
		expect(await screen.findByLabelText("Embed Code")).toHaveTextContent(
			"/embed/forms/public/public-key?theme=light&header=true&background=solid",
		);
		expect(screen.getByText("Shown")).toBeInTheDocument();
		expect(screen.getByText("Solid")).toBeInTheDocument();
	});

	it("updates embed display options and confirms unpublishing", async () => {
		mockAuthFetch
			.mockResolvedValueOnce(
				jsonResponse({
					...unpublished,
					status: "published",
					public_key: "public-key",
					allowed_origins: ["https://example.com"],
					approved_fingerprint: "sha256:reviewed",
					iframe_path: "/embed/forms/public/public-key",
				}),
			)
			.mockResolvedValueOnce(jsonResponse(review))
			.mockResolvedValueOnce(jsonResponse(form));

		const { user } = renderWithProviders(
			<FormShareDialog
				formId="form-1"
				formName="Customer intake"
				open
				onOpenChange={vi.fn()}
			/>,
		);

		await screen.findByLabelText("Private form link");
		await user.click(screen.getByRole("tab", { name: "Website Embed" }));
		const embedCode = await screen.findByLabelText("Embed Code");
		await user.click(screen.getByRole("combobox", { name: "Theme" }));
		await user.click(screen.getByRole("option", { name: "Dark" }));
		await user.click(screen.getByRole("switch", { name: "Show Header" }));
		await user.click(
			screen.getByRole("switch", { name: "Transparent Background" }),
		);

		expect(embedCode).toHaveTextContent(
			"/embed/forms/public/public-key?theme=dark&header=false&background=transparent",
		);
		expect(screen.getByText("Hidden")).toBeInTheDocument();
		expect(screen.getByText("Transparent")).toBeInTheDocument();
		const rotateButton = screen.getByRole("button", { name: "Rotate" });
		expect(rotateButton.parentElement).toHaveClass("justify-end");

		await user.click(screen.getByRole("switch", { name: "Published" }));
		expect(
			screen.getByRole("heading", { name: "Disable the public embed?" }),
		).toBeInTheDocument();
	});

	it("hides stale embed code and explains that capability changes pause it", async () => {
		mockAuthFetch
			.mockResolvedValueOnce(
				jsonResponse({
					...unpublished,
					status: "needs_review",
					public_key: "stale-key",
					iframe_path: "/embed/forms/public/stale-key",
				}),
			)
			.mockResolvedValueOnce(jsonResponse(review))
			.mockResolvedValueOnce(jsonResponse(form));

		const { user } = renderWithProviders(
			<FormShareDialog
				formId="form-1"
				formName="Customer intake"
				open
				onOpenChange={vi.fn()}
			/>,
		);

		await screen.findByLabelText("Private form link");
		expect(
			screen.queryByRole("heading", { name: "Confirmation Message" }),
		).not.toBeInTheDocument();
		await user.click(screen.getByRole("tab", { name: "Website Embed" }));
		expect(
			await screen.findByText(/existing embed is paused/i),
		).toBeInTheDocument();
		expect(screen.queryByLabelText("Embed Code")).not.toBeInTheDocument();
		expect(
			screen.getByRole("switch", { name: "Review Required" }),
		).not.toBeChecked();
		expect(screen.getByRole("button", { name: "Update" })).toBeDisabled();
	});

	it("saves the Confirmation Message from the sharing surface", async () => {
		mockAuthFetch
			.mockResolvedValueOnce(jsonResponse(unpublished))
			.mockResolvedValueOnce(jsonResponse(review))
			.mockResolvedValueOnce(jsonResponse(form))
			.mockResolvedValueOnce(jsonResponse({ ...form }));

		const { user } = renderWithProviders(
			<FormShareDialog
				formId="form-1"
				formName="Customer intake"
				open
				onOpenChange={vi.fn()}
			/>,
		);

		await screen.findByLabelText("Private form link");
		expect(
			screen.queryByRole("heading", { name: "Confirmation Message" }),
		).not.toBeInTheDocument();
		await user.click(screen.getByRole("tab", { name: "Website Embed" }));
		const markdown = await screen.findByLabelText(
			"Confirmation Message editor",
		);
		await user.clear(markdown);
		await user.type(markdown, "## Received\n\nWe will follow up soon.");
		await user.click(screen.getByRole("tab", { name: "Preview" }));
		expect(screen.getByRole("heading", { name: "Received" })).toBeVisible();
		expect(screen.getByText("We will follow up soon.")).toBeVisible();
		await user.click(screen.getByRole("button", { name: "Update" }));

		await waitFor(() => {
			expect(mockAuthFetch).toHaveBeenCalledWith(
				"/api/forms/form-1",
				expect.objectContaining({
					method: "PATCH",
					body: JSON.stringify({
						confirmation_markdown:
							"## Received\n\nWe will follow up soon.",
					}),
				}),
			);
		});
	});

	it("loads HMAC secret management in its own tab", async () => {
		mockAuthFetch
			.mockResolvedValueOnce(jsonResponse(unpublished))
			.mockResolvedValueOnce(jsonResponse(review))
			.mockResolvedValueOnce(jsonResponse(form))
			.mockResolvedValueOnce(jsonResponse([]));

		const { user } = renderWithProviders(
			<FormShareDialog
				formId="form-1"
				formName="Customer intake"
				open
				onOpenChange={vi.fn()}
			/>,
		);

		await screen.findByLabelText("Private form link");
		await user.click(screen.getByRole("tab", { name: "HMAC" }));
		expect(
			await screen.findByText("No embed secrets configured."),
		).toBeInTheDocument();
		expect(mockAuthFetch).toHaveBeenCalledWith(
			"/api/forms/form-1/embed-secrets",
		);
		expect(
			screen.queryByRole("heading", { name: "Confirmation Message" }),
		).not.toBeInTheDocument();
	});

	it("automatically saves Website Restrictions for a published embed", async () => {
		mockAuthFetch
			.mockResolvedValueOnce(
				jsonResponse({
					...unpublished,
					status: "published",
					public_key: "public-key",
					approved_fingerprint: "sha256:reviewed",
					iframe_path: "/embed/forms/public/public-key",
				}),
			)
			.mockResolvedValueOnce(jsonResponse(review))
			.mockResolvedValueOnce(jsonResponse(form))
			.mockResolvedValueOnce(jsonResponse({ ok: true }));

		const { user } = renderWithProviders(
			<FormShareDialog
				formId="form-1"
				formName="Customer intake"
				open
				onOpenChange={vi.fn()}
			/>,
		);

		await screen.findByLabelText("Private form link");
		await user.click(screen.getByRole("tab", { name: "Website Embed" }));
		await user.click(
			screen.getByRole("button", { name: /Website Restrictions/ }),
		);
		await user.type(
			screen.getByLabelText("Allowed Website Origins"),
			"https://example.com",
		);

		await waitFor(
			() => {
				expect(mockAuthFetch).toHaveBeenCalledWith(
					"/api/forms/form-1/publication",
					expect.objectContaining({
						method: "PUT",
						body: JSON.stringify({
							reviewed_fingerprint: "sha256:reviewed",
							allowed_origins: ["https://example.com"],
							spam_protection_enabled: true,
						}),
					}),
				);
			},
			{ timeout: 2000 },
		);
		expect(
			await screen.findByText("Restrictions saved"),
		).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Update" })).toBeDisabled();
	});

	it("saves Spam Protection immediately for a published embed", async () => {
		const published = {
			...unpublished,
			status: "published",
			public_key: "public-key",
			approved_fingerprint: "sha256:reviewed",
			iframe_path: "/embed/forms/public/public-key",
		};
		mockAuthFetch
			.mockResolvedValueOnce(jsonResponse(published))
			.mockResolvedValueOnce(jsonResponse(review))
			.mockResolvedValueOnce(jsonResponse(form))
			.mockResolvedValueOnce(
				jsonResponse({ ...published, spam_protection_enabled: false }),
			);

		const { user } = renderWithProviders(
			<FormShareDialog
				formId="form-1"
				formName="Customer intake"
				open
				onOpenChange={vi.fn()}
			/>,
		);

		await screen.findByLabelText("Private form link");
		await user.click(screen.getByRole("tab", { name: "Website Embed" }));
		const spamProtection = screen.getByRole("switch", {
			name: "Spam Protection",
		});
		expect(spamProtection).toBeChecked();
		await user.click(spamProtection);

		await waitFor(() => {
			expect(mockAuthFetch).toHaveBeenCalledWith(
				"/api/forms/form-1/publication",
				expect.objectContaining({
					method: "PUT",
					body: JSON.stringify({
						reviewed_fingerprint: "sha256:reviewed",
						allowed_origins: [],
						spam_protection_enabled: false,
					}),
				}),
			);
		});
	});
});

it("keeps publication disabled when sharing settings cannot be loaded", async () => {
	mockAuthFetch.mockResolvedValue(jsonResponse({}, false));
	const { user } = renderWithProviders(<FormShareDialog formId="form-1" formName="Customer intake" open onOpenChange={vi.fn()} />);
	await user.click(screen.getByRole("tab", { name: "Website Embed" }));
	expect(await screen.findByText("Sharing settings could not be loaded")).toBeInTheDocument();
	expect(screen.getByRole("switch", { name: "Not Published" })).toBeDisabled();
});

it("isolates a new form draft from the previous form's delayed response", async () => {
	let release!: (response: Response) => void;
	const delayed = new Promise<Response>(resolve => { release = resolve; });
	mockAuthFetch.mockImplementation((url: string) => {
		if (url === "/api/forms/form-1") return delayed;
		if (url.endsWith("/publication")) return Promise.resolve(jsonResponse(unpublished));
		if (url.endsWith("/publication-review")) return Promise.resolve(jsonResponse(review));
		return Promise.resolve(jsonResponse({ ...form, id: "form-2", confirmation_markdown: "Second form message" }));
	});
	const onOpenChange = vi.fn();
	const { user, rerender } = renderWithProviders(<FormShareDialog formId="form-1" formName="First form" open onOpenChange={onOpenChange} />);
	await waitFor(() => expect(mockAuthFetch).toHaveBeenCalledWith("/api/forms/form-1"));
	rerender(<FormShareDialog formId="form-2" formName="Second form" open onOpenChange={onOpenChange} />);
	await user.click(screen.getByRole("tab", { name: "Website Embed" }));
	const editor = await screen.findByLabelText("Confirmation Message editor");
	await waitFor(() => expect(editor).toHaveValue("Second form message"));
	await user.clear(editor);
	await user.type(editor, "Second form unsaved draft");
	await act(async () => { release(jsonResponse({ ...form, confirmation_markdown: "Late first form message" })); await delayed; });
	expect(screen.getByLabelText("Confirmation Message editor")).toHaveValue("Second form unsaved draft");
	expect(screen.getByRole("button", { name: "Update" })).toBeEnabled();
});

it("preserves an unsaved confirmation draft when rotating the embed refreshes settings", async () => {
	const published = { ...unpublished, status: "published", public_key: "synthetic-key", iframe_path: "/embed/forms/public/synthetic-key" };
	mockAuthFetch.mockImplementation((url: string) => {
		if (url.endsWith("/publication")) return Promise.resolve(jsonResponse(published));
		if (url.endsWith("/publication-review")) return Promise.resolve(jsonResponse(review));
		return Promise.resolve(jsonResponse(form));
	});
	const { user } = renderWithProviders(<FormShareDialog formId="form-1" formName="Customer intake" open onOpenChange={vi.fn()} />);
	await user.click(screen.getByRole("tab", { name: "Website Embed" }));
	const editor = await screen.findByLabelText("Confirmation Message editor");
	await user.clear(editor);
	await user.type(editor, "Unsaved confirmation draft");
	await user.click(screen.getByRole("button", { name: "Rotate" }));
	await user.click(screen.getByRole("button", { name: "Rotate" }));
	await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
	expect(await screen.findByLabelText("Confirmation Message editor")).toHaveValue("Unsaved confirmation draft");
	expect(screen.getByRole("button", { name: "Update" })).toBeEnabled();
});

it("ignores confirmation data from a refresh started before a newer save completed", async () => {
	let finishSave!: (response: Response) => void;
	let finishRefresh!: (response: Response) => void;
	const save = new Promise<Response>(resolve => { finishSave = resolve; });
	const refresh = new Promise<Response>(resolve => { finishRefresh = resolve; });
	let reads = 0;
	mockAuthFetch.mockImplementation((url: string, options?: RequestInit) => {
		if (options?.method === "PATCH") return save;
		if (url.endsWith("/publication")) return Promise.resolve(jsonResponse({ ...unpublished, status: "published", iframe_path: "/embed/forms/public/synthetic" }));
		if (url.endsWith("/publication-review")) return Promise.resolve(jsonResponse(review));
		if (url === "/api/forms/form-1") return ++reads === 1 ? Promise.resolve(jsonResponse(form)) : refresh;
		return Promise.resolve(jsonResponse({}));
	});
	const { user } = renderWithProviders(<FormShareDialog formId="form-1" formName="Customer intake" open onOpenChange={vi.fn()} />);
	await user.click(screen.getByRole("tab", { name: "Website Embed" }));
	const editor = await screen.findByLabelText("Confirmation Message editor");
	await user.clear(editor);
	await user.type(editor, "Newly saved confirmation");
	await user.click(screen.getByRole("button", { name: "Update" }));
	await user.click(screen.getByRole("button", { name: "Rotate" }));
	await user.click(screen.getByRole("button", { name: "Rotate" }));
	await waitFor(() => expect(reads).toBe(2));
	await act(async () => { finishSave(jsonResponse({})); await save; });
	await act(async () => { finishRefresh(jsonResponse(form)); await refresh; });
	await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
	expect(await screen.findByLabelText("Confirmation Message editor")).toHaveValue("Newly saved confirmation");
	expect(screen.getByRole("button", { name: "Update" })).toBeDisabled();
});

it("preserves origin edits when rotation refreshes before autosave", async () => {
	mockAuthFetch.mockImplementation((url: string) => {
		if (url.endsWith("/publication")) return Promise.resolve(jsonResponse({ ...unpublished, status: "published", iframe_path: "/embed/forms/public/synthetic" }));
		if (url.endsWith("/publication-review")) return Promise.resolve(jsonResponse(review));
		return Promise.resolve(jsonResponse(form));
	});
	const { user } = renderWithProviders(<FormShareDialog formId="form-1" formName="Customer intake" open onOpenChange={vi.fn()} />);
	await user.click(screen.getByRole("tab", { name: "Website Embed" }));
	await user.click(await screen.findByRole("button", { name: "Website Restrictions Optional" }));
	await user.type(screen.getByLabelText("Allowed Website Origins"), "https://new.example.com");
	await user.click(screen.getByRole("button", { name: "Rotate" }));
	await user.click(screen.getByRole("button", { name: "Rotate" }));
	await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
	expect(await screen.findByLabelText("Allowed Website Origins")).toHaveValue("https://new.example.com");
	await waitFor(() => expect(mockAuthFetch).toHaveBeenCalledWith("/api/forms/form-1/publication", expect.objectContaining({ method: "PUT", body: expect.stringContaining("https://new.example.com") })));
});

it.each([true, false])("flushes origins before close and only closes after success: %s", async success => {
	let finish!: (response: Response) => void;
	const save = new Promise<Response>(resolve => { finish = resolve; });
	mockAuthFetch.mockImplementation((url: string, options?: RequestInit) => {
		if (options?.method === "PUT") return save;
		if (url.endsWith("/publication")) return Promise.resolve(jsonResponse({ ...unpublished, status: "published", iframe_path: "/embed/forms/public/synthetic" }));
		if (url.endsWith("/publication-review")) return Promise.resolve(jsonResponse(review));
		return Promise.resolve(jsonResponse(form));
	});
	const onOpenChange = vi.fn();
	const { user } = renderWithProviders(<FormShareDialog formId="form-1" formName="Customer intake" open onOpenChange={onOpenChange} />);
	await user.click(screen.getByRole("tab", { name: "Website Embed" }));
	await user.click(await screen.findByRole("button", { name: "Website Restrictions Optional" }));
	await user.type(screen.getByLabelText("Allowed Website Origins"), "https://draft.example.com");
	await user.click(screen.getByRole("button", { name: "Close" }));
	expect(onOpenChange).not.toHaveBeenCalled();
	expect(mockAuthFetch).toHaveBeenCalledWith("/api/forms/form-1/publication", expect.objectContaining({ method: "PUT", body: expect.stringContaining("https://draft.example.com") }));
	await act(async () => { finish(jsonResponse({}, success)); await save; });
	if (success) expect(onOpenChange).toHaveBeenCalledWith(false);
	else {
		expect(onOpenChange).not.toHaveBeenCalled();
		expect(screen.getByLabelText("Allowed Website Origins")).toHaveValue("https://draft.example.com");
		expect(screen.getByRole("button", { name: "Retry saving" })).toBeEnabled();
		expect(screen.getByRole("button", { name: "Retry saving" })).toHaveFocus();
	}
});
