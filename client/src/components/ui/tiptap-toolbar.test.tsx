import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TiptapToolbar } from "./tiptap-toolbar";

const mockEditor = {
	chain: () => ({
		focus: () => ({
			undo: () => ({ run: vi.fn() }),
			redo: () => ({ run: vi.fn() }),
			toggleHeading: () => ({ run: vi.fn() }),
			toggleBold: () => ({ run: vi.fn() }),
			toggleItalic: () => ({ run: vi.fn() }),
			toggleStrike: () => ({ run: vi.fn() }),
			toggleCode: () => ({ run: vi.fn() }),
			toggleBulletList: () => ({ run: vi.fn() }),
			toggleOrderedList: () => ({ run: vi.fn() }),
			toggleBlockquote: () => ({ run: vi.fn() }),
			setLink: () => ({ run: vi.fn() }),
		}),
	}),
	can: () => ({
		undo: () => true,
		redo: () => true,
	}),
	isActive: () => false,
} as const;

describe("TiptapToolbar", () => {
	it("gives each icon control an accessible name and touch-sized hit area", () => {
		render(<TiptapToolbar editor={mockEditor as never} />);

		expect(screen.getByRole("group")).toHaveAttribute(
			"aria-label",
			"Rich text formatting",
		);
		expect(screen.getByRole("button", { name: "Undo" })).toHaveClass(
			"h-11",
			"w-11",
			"sm:h-10",
			"sm:w-10",
		);
		expect(screen.getByRole("button", { name: "Redo" })).toHaveClass(
			"h-11",
			"w-11",
		);
		expect(screen.getByRole("button", { name: "Heading level 2" })).toHaveClass(
			"h-11",
			"w-11",
		);
		expect(screen.getByRole("button", { name: "Insert link" })).toHaveClass(
			"h-11",
			"w-11",
		);
		expect(screen.getByRole("button", { name: "Block quote" })).toHaveClass(
			"h-11",
			"w-11",
		);
	});
});
