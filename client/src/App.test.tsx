import { useEffect } from "react";
import {
	Link,
	Outlet,
	RouterProvider,
	createMemoryRouter,
} from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppFrame } from "./App";

vi.mock("@/contexts/OrgScopeContext", () => ({
	useOrgScope: () => ({ brandingLoaded: true }),
	OrgScopeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/lib/applicationName", () => ({
	useApplicationName: () => "Bifrost",
}));

vi.mock("@/contexts/KeyboardContext", () => ({
	useCmdCtrlShortcut: vi.fn(),
	KeyboardProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/stores/quickAccessStore", () => ({
	useQuickAccessStore: (selector: (state: unknown) => unknown) =>
		selector({
			isOpen: false,
			openQuickAccess: vi.fn(),
			closeQuickAccess: vi.fn(),
		}),
}));

vi.mock("@/stores/editorStore", () => ({
	useEditorStore: (selector: (state: unknown) => unknown) =>
		selector({
			isOpen: false,
			openEditor: vi.fn(),
		}),
}));

vi.mock("@/components/quick-access/QuickAccess", () => ({
	QuickAccess: () => null,
}));

vi.mock("@/components/editor/EditorOverlay", () => ({
	EditorOverlay: () => null,
}));

vi.mock("@/components/layout/UnifiedDock", () => ({
	UnifiedDock: () => null,
}));

vi.mock("@/components/ApplicationUpdateScreen", () => ({
	ApplicationUpdateGate: ({ children }: { children: React.ReactNode }) =>
		children,
}));

function PersistentLayout({ onMount }: { onMount: () => void }) {
	useEffect(() => {
		onMount();
	}, [onMount]);

	return (
		<div>
			<nav aria-label="Shell navigation">
				<Link to="/agents">Agents</Link>
				<Link to="/users">Users</Link>
			</nav>
			<Outlet />
		</div>
	);
}

describe("AppFrame shell lifetime", () => {
	it("keeps the shell layout mounted while sibling platform routes change", async () => {
		const onLayoutMount = vi.fn();
		const router = createMemoryRouter(
			[
				{
					element: <AppFrame />,
					children: [
						{
							path: "/",
							element: <PersistentLayout onMount={onLayoutMount} />,
							children: [
								{ path: "agents", element: <h1>Agents</h1> },
								{ path: "users", element: <h1>Users</h1> },
							],
						},
					],
				},
			],
			{ initialEntries: ["/agents"] },
		);

		render(<RouterProvider router={router} />);
		expect(await screen.findByRole("heading", { name: "Agents" })).toBeVisible();
		expect(onLayoutMount).toHaveBeenCalledTimes(1);

		await userEvent.setup().click(screen.getByRole("link", { name: "Users" }));

		expect(await screen.findByRole("heading", { name: "Users" })).toBeVisible();
		expect(onLayoutMount).toHaveBeenCalledTimes(1);
	});
});
