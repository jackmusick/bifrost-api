import {
	renderWithProviders as render,
	screen,
	fireEvent,
	waitFor,
	act,
} from "@/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/services/filePolicies", () => ({
	listFilePolicies: vi.fn(),
	saveFilePolicy: vi.fn(),
	deleteFilePolicy: vi.fn(),
}));
vi.mock("@/services/policyRules", () => ({
	listPolicyRules: vi.fn().mockResolvedValue([]),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
// Monaco can't run in the test DOM — stub it to a textarea labelled by `path`.
vi.mock("@monaco-editor/react", () => ({
	default: ({
		value,
		onChange,
		path,
	}: {
		value?: string;
		onChange?: (v: string | undefined) => void;
		path?: string;
	}) => (
		<textarea
			aria-label={path ?? "monaco-editor"}
			value={value ?? ""}
			onChange={(e) => onChange?.(e.target.value)}
		/>
	),
}));
vi.mock("@/contexts/ThemeContext", () => ({
	useTheme: () => ({ theme: "light" }),
}));
import { listFilePolicies, saveFilePolicy } from "@/services/filePolicies";
import { PolicyEditorModal, PolicyEditorPanel } from "./PolicyEditorModal";

describe("PolicyEditorModal", () => {
	beforeEach(() => {
		vi.mocked(listFilePolicies).mockReset();
		vi.mocked(saveFilePolicy).mockReset();
	});

	it("loads the best policy and saves edits with the right scope/location", async () => {
		vi.mocked(listFilePolicies).mockResolvedValue({
			policies: [
				{
					id: "p1",
					location: "gallery",
					path: "",
					organizationId: null,
					policies: { policies: [] },
				},
			],
		});
		vi.mocked(saveFilePolicy).mockResolvedValue({
			id: "p1",
			location: "gallery",
			path: "",
			organizationId: null,
			policies: { policies: [] },
		});
		const onSaved = vi.fn();
		render(
			<PolicyEditorModal
				open
				onOpenChange={vi.fn()}
				location="gallery"
				scope={null}
				path="pic.png"
				onSaved={onSaved}
			/>,
		);
		// Editor renders once the best policy resolves.
		await waitFor(() =>
			expect(
				screen.getByRole("button", { name: /save policy/i }),
			).toBeInTheDocument(),
		);
		fireEvent.click(screen.getByRole("button", { name: /save policy/i }));
		await waitFor(() => expect(saveFilePolicy).toHaveBeenCalled());
		const saved = vi.mocked(saveFilePolicy).mock.calls[0][0];
		expect(saved.location).toBe("gallery");
		expect(saved.organizationId).toBeNull();
		await waitFor(() => expect(onSaved).toHaveBeenCalled());
	});
	it("does not invent a default policy after a failed load and offers retry", async () => {
		vi.mocked(listFilePolicies)
			.mockRejectedValueOnce(new Error("Unavailable"))
			.mockResolvedValueOnce({ policies: [] });
		render(
			<PolicyEditorModal
				open
				onOpenChange={vi.fn()}
				location="gallery"
				scope={null}
				path="reports/"
			/>,
		);
		await screen.findByText("File policy could not be loaded");
		expect(
			screen.queryByLabelText("file-policies.yaml"),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /save policy/i }),
		).not.toBeInTheDocument();
		fireEvent.click(
			screen.getByRole("button", { name: "Retry File Policy" }),
		);
		expect(
			await screen.findByRole("button", { name: /save policy/i }),
		).toBeInTheDocument();
	});
	it("keeps a late response for another path out of the current draft", async () => {
		let resolveOld: (value: { policies: [] }) => void = () => {};
		vi.mocked(listFilePolicies)
			.mockImplementationOnce(
				() =>
					new Promise((resolve) => {
						resolveOld = resolve;
					}),
			)
			.mockResolvedValueOnce({ policies: [] });
		const onOpenChange = vi.fn();
		const { rerender } = render(
			<PolicyEditorModal
				open
				onOpenChange={onOpenChange}
				location="gallery"
				scope={null}
				path="old/"
			/>,
		);
		rerender(
			<PolicyEditorModal
				open
				onOpenChange={onOpenChange}
				location="gallery"
				scope={null}
				path="current/"
			/>,
		);
		await screen.findByRole("button", { name: /save policy/i });
		await act(async () => resolveOld({ policies: [] }));
		fireEvent.click(screen.getByRole("button", { name: /save policy/i }));
		await waitFor(() => expect(saveFilePolicy).toHaveBeenCalled());
		expect(vi.mocked(saveFilePolicy).mock.calls[0][0].path).toBe(
			"current/",
		);
	});

	it("keeps the modal open during a pending save and retains the draft after failure", async () => {
		vi.mocked(listFilePolicies).mockResolvedValue({ policies: [] });
		let rejectSave: (reason: Error) => void = () => {};
		vi.mocked(saveFilePolicy)
			.mockImplementationOnce(
				() =>
					new Promise((_, reject) => {
						rejectSave = reject;
					}),
			)
			.mockImplementationOnce(async (policy) => policy);
		const onOpenChange = vi.fn();
		render(
			<PolicyEditorModal
				open
				onOpenChange={onOpenChange}
				location="gallery"
				scope={null}
				path="reports/"
			/>,
		);
		await screen.findByRole("switch", { name: /^advanced$/i });
		fireEvent.click(screen.getByRole("switch", { name: /^advanced$/i }));
		const editor = await screen.findByLabelText("file-policies.yaml");
		const initialDraft = (editor as HTMLTextAreaElement).value;
		fireEvent.click(screen.getByRole("button", { name: "Save Policy" }));
		await screen.findByRole("button", { name: /Saving/ });
		fireEvent.keyDown(document, { key: "Escape" });
		expect(onOpenChange).not.toHaveBeenCalled();
		await act(async () => rejectSave(new Error("Temporary save failure")));
		await screen.findByText("Temporary save failure");
		expect(editor).toHaveValue(initialDraft);
		expect(onOpenChange).not.toHaveBeenCalled();
		fireEvent.click(screen.getByRole("button", { name: "Save Policy" }));
		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		expect(vi.mocked(saveFilePolicy).mock.calls[1][0]).toEqual(
			vi.mocked(saveFilePolicy).mock.calls[0][0],
		);
	});

	it("edits an exact policy path when embedded", async () => {
		vi.mocked(listFilePolicies).mockResolvedValue({
			policies: [
				{
					id: "ancestor",
					location: "gallery",
					path: "",
					organizationId: null,
					policies: { policies: [] },
				},
				{
					id: "folder",
					location: "gallery",
					path: "reports/",
					organizationId: null,
					policies: { policies: [] },
				},
			],
		});
		vi.mocked(saveFilePolicy).mockImplementation(async (policy) => policy);
		render(
			<PolicyEditorPanel
				location="gallery"
				scope={null}
				path="reports/june.txt"
				exactPath="reports/"
			/>,
		);
		await screen.findByText("Editing the policy attached to this path.");
		fireEvent.click(screen.getByRole("button", { name: /save policy/i }));
		await waitFor(() => expect(saveFilePolicy).toHaveBeenCalled());
		expect(vi.mocked(saveFilePolicy).mock.calls[0][0].id).toBe("folder");
		expect(vi.mocked(saveFilePolicy).mock.calls[0][0].path).toBe(
			"reports/",
		);
	});

	it("creates a blank exact policy and clears busy before embedded close", async () => {
		vi.mocked(listFilePolicies).mockResolvedValue({
			policies: [
				{
					id: "ancestor",
					location: "gallery",
					path: "",
					organizationId: null,
					policies: { policies: [] },
				},
			],
		});
		vi.mocked(saveFilePolicy).mockImplementation(async (policy) => policy);
		const events: string[] = [];
		render(
			<PolicyEditorPanel
				location="gallery"
				scope={null}
				path="reports/june.txt"
				exactPath="reports/"
				onBusyChange={(busy) => events.push(`busy:${busy}`)}
				onOpenChange={(open) => events.push(`open:${open}`)}
			/>,
		);
		await screen.findByRole("button", { name: /save policy/i });
		fireEvent.click(screen.getByRole("button", { name: /save policy/i }));
		await waitFor(() =>
			expect(events).toEqual(
				expect.arrayContaining(["busy:false", "open:false"]),
			),
		);
		const saved = vi.mocked(saveFilePolicy).mock.calls[0][0];
		expect(saved.id).toBeUndefined();
		expect(saved.path).toBe("reports/");
		expect(events.indexOf("busy:false")).toBeLessThan(
			events.indexOf("open:false"),
		);
	});
	it("keeps inherited access read-only and saves a new policy on the selected file", async () => {
		const root = {
			id: "root",
			location: "gallery",
			path: "",
			organizationId: null,
			policies: { policies: [] },
		};
		vi.mocked(listFilePolicies).mockResolvedValue({ policies: [root] });
		vi.mocked(saveFilePolicy).mockImplementation(async (policy) => policy);
		const onOpenSource = vi.fn();
		render(
			<PolicyEditorPanel
				location="gallery"
				scope={null}
				path="onboarding/customer.json"
				onOpenSource={onOpenSource}
			/>,
		);
		await screen.findByRole("region", { name: "Inherited Access" });
		expect(screen.getByText("Read-Only")).toBeInTheDocument();
		fireEvent.click(
			screen.getByRole("button", { name: "gallery / Share root" }),
		);
		expect(onOpenSource).toHaveBeenCalledWith(root);
		expect(saveFilePolicy).not.toHaveBeenCalled();
		fireEvent.click(screen.getByRole("button", { name: "Save Policy" }));
		await waitFor(() => expect(saveFilePolicy).toHaveBeenCalled());
		expect(vi.mocked(saveFilePolicy).mock.calls[0][0]).toMatchObject({
			path: "onboarding/customer.json",
			location: "gallery",
			organizationId: null,
		});
		expect(vi.mocked(saveFilePolicy).mock.calls[0][0].id).toBeUndefined();
	});
	it("does not describe the share root as inheriting itself", async () => {
		vi.mocked(listFilePolicies).mockResolvedValue({
			policies: [
				{
					id: "root",
					location: "gallery",
					path: "",
					organizationId: null,
					policies: { policies: [] },
				},
			],
		});
		render(<PolicyEditorPanel location="gallery" scope={null} path="" />);
		await screen.findByRole("button", { name: "Save Policy" });
		expect(
			screen.queryByRole("region", { name: "Inherited Access" }),
		).not.toBeInTheDocument();
	});
});
