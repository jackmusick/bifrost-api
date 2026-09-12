import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { CollectionIconPicker } from "./CollectionIconPicker";

describe("CollectionIconPicker", () => {
	it("filters icons and reports the chosen icon", async () => {
		const onChange = vi.fn();
		const { user } = renderWithProviders(
			<CollectionIconPicker value="folder" onChange={onChange} />,
		);

		await user.type(
			screen.getByLabelText("Search collection icons"),
			"rocket",
		);
		expect(
			screen.getByRole("button", { name: "rocket" }),
		).toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: "folder" }),
		).not.toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: "rocket" }));
		expect(onChange).toHaveBeenCalledWith("rocket");
	});

	it("shows an empty icon result when no icons match", async () => {
		const { user } = renderWithProviders(
			<CollectionIconPicker value="folder" onChange={vi.fn()} />,
		);

		await user.type(
			screen.getByLabelText("Search collection icons"),
			"not-a-real-icon",
		);
		expect(screen.getByText("No matching icons.")).toBeInTheDocument();
	});
});
