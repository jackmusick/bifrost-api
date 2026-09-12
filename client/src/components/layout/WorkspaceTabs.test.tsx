import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { WorkspaceTabs } from "./WorkspaceTabs";
const state = vi.hoisted(() => ({ admin: true }));
vi.mock("@/contexts/AuthContext", () => ({
	useAuth: () => ({ isPlatformAdmin: state.admin }),
}));
describe("WorkspaceTabs", () => {
	it("links the dashboard and Home with the active route identified", () => {
		state.admin = true;
		renderWithProviders(<WorkspaceTabs />, {
			initialEntries: ["/dashboard"],
		});
		expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute(
			"aria-current",
			"page",
		);
		expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute(
			"href",
			"/",
		);
	});
	it("does not show administrative tabs to ordinary users", () => {
		state.admin = false;
		renderWithProviders(<WorkspaceTabs />);
		expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
	});
});
