import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { EditorFileStatus } from "./EditorFileStatus";

describe("EditorFileStatus", () => {
	it("makes the full path and file information accessible by keyboard", async () => {
		const user = userEvent.setup();
		const path = "folder/nested/complete_workflow_name.py";
		render(<EditorFileStatus path={path} isWorkflow saveState="dirty" language="python" cursor={{ line: 42, column: 8 }} />);
		expect(screen.getByRole("status")).toHaveTextContent("Unsaved changes");
		const trigger = screen.getByRole("button", { name: `File details for ${path}` });
		trigger.focus();
		await user.keyboard("{Enter}");
		expect(screen.getByText(path)).toBeVisible();
		expect(screen.getByText("Line 42, column 8")).toBeVisible();
		await user.keyboard("{Escape}");
		expect(trigger).toHaveFocus();
	});
	it("uses a stable saved label rather than inventing a new save time on render", () => {
		render(<EditorFileStatus path="file.txt" isWorkflow={false} saveState="saved" language="" cursor={{ line: 1, column: 1 }} />);
		expect(screen.getByRole("status")).toHaveTextContent(/^Saved$/);
	});
});
