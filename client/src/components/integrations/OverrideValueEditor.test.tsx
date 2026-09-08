import { expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { OverrideValueEditor } from "./OverrideValueEditor";

it("blocks invalid JSON without discarding the draft", async () => {
	const onSave = vi.fn();
	const { user } = renderWithProviders(
		<OverrideValueEditor
			name="options"
			type="json"
			value="{"
			pending={false}
			error={null}
			onChange={() => {}}
			onSave={onSave}
			onCancel={() => {}}
		/>,
	);
	await user.click(screen.getByRole("button", { name: "Save value" }));
	expect(screen.getByRole("alert")).toHaveTextContent("Enter valid JSON.");
	expect(onSave).not.toHaveBeenCalled();
});
it("Cancel and blur do not save, while explicit save preserves numeric zero", async () => {
	const onSave = vi.fn();
	const onCancel = vi.fn();
	const { user } = renderWithProviders(
		<OverrideValueEditor
			name="count"
			type="int"
			value="0"
			pending={false}
			error={null}
			onChange={() => {}}
			onSave={onSave}
			onCancel={onCancel}
		/>,
	);
	await user.click(screen.getByRole("button", { name: "Cancel" }));
	expect(onCancel).toHaveBeenCalledOnce();
	expect(onSave).not.toHaveBeenCalled();
	await user.click(screen.getByRole("button", { name: "Save value" }));
	expect(onSave).toHaveBeenCalledWith(0);
});

it("does not submit whitespace as JSON", async () => {
	const onSave = vi.fn();
	const { user } = renderWithProviders(
		<OverrideValueEditor
			name="options"
			type="json"
			value="   "
			pending={false}
			error={null}
			onChange={() => {}}
			onSave={onSave}
			onCancel={() => {}}
		/>,
	);
	await user.click(screen.getByRole("button", { name: "Save value" }));
	expect(onSave).not.toHaveBeenCalled();
	expect(screen.getByRole("alert")).toHaveTextContent("Enter valid JSON.");
});
