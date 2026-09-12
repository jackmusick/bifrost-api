import { describe, expect, it, vi } from "vitest";
import { fireEvent, renderWithProviders, screen, waitFor } from "@/test-utils";

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

import { CustomClaimEditor } from "./CustomClaimEditor";
import type { CustomClaim } from "@/services/claims";

const claim: CustomClaim = {
	id: "11111111-1111-4111-8111-111111111111",
	organization_id: "22222222-2222-4222-8222-222222222222",
	solution_id: null,
	name: "allowed_campus_ids",
	description: "",
	type: "list",
	query: { table: "user_campus_access", select: "campus_id" },
	is_solution_managed: false,
};

describe("CustomClaimEditor", () => {
	it("renders the claim fields", () => {
		renderWithProviders(
			<CustomClaimEditor
				value={claim}
				onChange={vi.fn()}
				onSave={vi.fn()}
				onCancel={vi.fn()}
			/>,
		);

		expect(screen.getByDisplayValue("allowed_campus_ids")).toBeVisible();
		expect(screen.getByDisplayValue("list")).toBeVisible();
		expect(screen.getByLabelText("claim-query.json")).toHaveValue(
			JSON.stringify(claim.query, null, 2),
		);
	});

	it("disables Save when the query is invalid", () => {
		renderWithProviders(
			<CustomClaimEditor
				value={{
					...claim,
					query: null as unknown as CustomClaim["query"],
				}}
				onChange={vi.fn()}
				onSave={vi.fn()}
				onCancel={vi.fn()}
			/>,
		);

		expect(screen.getByRole("button", { name: /save/i })).toBeDisabled();
	});

	it("invokes onSave with the current value", () => {
		const onSave = vi.fn();
		renderWithProviders(
			<CustomClaimEditor
				value={claim}
				onChange={vi.fn()}
				onSave={onSave}
				onCancel={vi.fn()}
			/>,
		);

		fireEvent.click(screen.getByRole("button", { name: /save/i }));

		expect(onSave).toHaveBeenCalledWith(claim);
	});
	it("blocks saving a broken or empty draft instead of the last valid query", () => {
		const onSave = vi.fn();
		renderWithProviders(
			<CustomClaimEditor
				value={claim}
				onChange={vi.fn()}
				onSave={onSave}
				onCancel={vi.fn()}
			/>,
		);
		const editor = screen.getByLabelText("claim-query.json");
		const save = screen.getByRole("button", { name: /^save$/i });
		fireEvent.change(editor, { target: { value: "{" } });
		expect(save).toBeDisabled();
		fireEvent.click(save);
		expect(onSave).not.toHaveBeenCalled();
		fireEvent.change(editor, {
			target: { value: JSON.stringify(claim.query) },
		});
		expect(save).toBeEnabled();
		fireEvent.change(editor, { target: { value: "" } });
		expect(editor).toHaveValue("");
		expect(save).toBeDisabled();
	});
	it("retains the claim after a failed save and focuses recovery", async () => {
		let rejectSave!: (cause: Error) => void;
		const onSave = vi
			.fn()
			.mockImplementationOnce(
				() =>
					new Promise<void>((_, reject) => {
						rejectSave = reject;
					}),
			)
			.mockResolvedValue(undefined);
		const { user } = renderWithProviders(
			<CustomClaimEditor
				value={claim}
				onChange={vi.fn()}
				onSave={onSave}
				onCancel={vi.fn()}
			/>,
		);
		await user.click(screen.getByRole("button", { name: /^save$/i }));
		expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
		expect(screen.getByLabelText("Description")).toBeDisabled();
		rejectSave(new Error("Synthetic save failure"));
		await waitFor(() => expect(screen.getByRole("alert")).toHaveFocus());
		expect(screen.getByDisplayValue(claim.name)).toBeVisible();
		await user.click(screen.getByRole("button", { name: /^save$/i }));
		expect(onSave).toHaveBeenCalledTimes(2);
		expect(onSave.mock.calls[1][0]).toEqual(claim);
	});
});
