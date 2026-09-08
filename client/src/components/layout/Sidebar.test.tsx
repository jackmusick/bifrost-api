import userEvent from "@testing-library/user-event";
import { within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { TerminologyContext, mergeTerminology } from "@/lib/terminology";
import { Sidebar } from "./Sidebar";

vi.mock("@/contexts/AuthContext", () => ({
	useAuth: () => ({ isPlatformAdmin: true }),
}));

vi.mock("@/components/branding/Logo", () => ({
	Logo: () => <div aria-label="Logo" />,
}));

describe("Sidebar terminology", () => {
	it("renders branded product nouns in navigation", () => {
		const terminology = mergeTerminology({
			app: { singular: "Game", plural: "Games" },
			agent: { singular: "Character", plural: "Characters" },
			form: { singular: "Quest", plural: "Quests" },
		});

		renderWithProviders(
			<TerminologyContext.Provider value={terminology}>
				<Sidebar
					isMobileMenuOpen={false}
					setIsMobileMenuOpen={vi.fn()}
					isCollapsed={false}
				/>
			</TerminologyContext.Provider>,
		);

		expect(screen.getByRole("link", { name: "Games" })).toHaveAttribute(
			"href",
			"/apps",
		);
		expect(
			screen.getByRole("link", { name: "Characters" }),
		).toHaveAttribute("href", "/agents");
		expect(screen.getByRole("link", { name: "Quests" })).toHaveAttribute(
			"href",
			"/forms",
		);
	});
});

describe("Sidebar mobile navigation", () => {
	it("exposes a named modal and lets Escape dismiss it", async () => {
		const close = vi.fn();
		renderWithProviders(
			<Sidebar
				isMobileMenuOpen
				setIsMobileMenuOpen={close}
				isCollapsed={false}
			/>,
		);
		const dialog = screen.getByRole("dialog", { name: "Navigation" });
		expect(
			within(dialog).getByRole("navigation", {
				name: "Primary navigation",
			}),
		).toBeInTheDocument();
		await userEvent.setup().keyboard("{Escape}");
		expect(close).toHaveBeenCalledWith(false);
	});
	it("closes after a mobile destination is selected", async () => {
		const close = vi.fn();
		renderWithProviders(
			<Sidebar
				isMobileMenuOpen
				setIsMobileMenuOpen={close}
				isCollapsed={false}
			/>,
		);
		const dialog = screen.getByRole("dialog", { name: "Navigation" });
		await userEvent
			.setup()
			.click(within(dialog).getByRole("link", { name: "Workflows" }));
		expect(close).toHaveBeenCalledWith(false);
	});
});
