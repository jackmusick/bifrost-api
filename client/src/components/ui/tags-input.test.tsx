import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { TagsInput } from "./tags-input";
function Example() {
	const [tags, setTags] = useState<string[]>([]);
	return (
		<>
			<TagsInput
				value={tags}
				onChange={setTags}
				validate={(tag) => !tag.includes("!")}
			/>
			<button>Next field</button>
		</>
	);
}
describe("TagsInput keyboard access", () => {
	it("commits on Tab and lets focus leave an empty input", async () => {
		const user = userEvent.setup();
		render(<Example />);
		const input = screen.getByRole("textbox");
		await user.click(input);
		await user.type(input, "alpha");
		await user.tab();
		expect(
			screen.getByRole("button", { name: "Remove alpha" }),
		).toBeVisible();
		expect(input).not.toHaveFocus();
		await user.click(input);
		await user.tab();
		expect(
			screen.getByRole("button", { name: "Next field" }),
		).toHaveFocus();
	});
	it("associates invalid feedback and returns focus after removing a tag", async () => {
		const user = userEvent.setup();
		render(<Example />);
		const input = screen.getByRole("textbox");
		await user.type(input, "bad!{Enter}");
		expect(input).toHaveAttribute("aria-invalid", "true");
		expect(input).toHaveAccessibleDescription("Invalid input");
		await user.clear(input);
		await user.type(input, "alpha{Enter}");
		await user.click(screen.getByRole("button", { name: "Remove alpha" }));
		expect(input).toHaveFocus();
		expect(
			screen.queryByRole("button", { name: "Remove alpha" }),
		).not.toBeInTheDocument();
	});
});
