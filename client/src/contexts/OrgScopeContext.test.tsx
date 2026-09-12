import { afterEach, expect, it, vi } from "vitest";
import { useState } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { OrgScopeProvider, useOrgScope } from "./OrgScopeContext";

vi.mock("@/lib/branding", () => ({
	initializeBranding: vi.fn(),
	applyBrandingTheme: vi.fn(),
}));
afterEach(() => vi.unstubAllGlobals());

function Draft() {
	const [value, setValue] = useState("");
	return (
		<input
			aria-label="Draft"
			value={value}
			onChange={(event) => setValue(event.target.value)}
		/>
	);
}
function Shell() {
	const { brandingLoaded, applicationName, refreshBranding } = useOrgScope();
	if (!brandingLoaded) return <p>Loading branding</p>;
	return (
		<>
			<span>{applicationName}</span>
			<button onClick={refreshBranding}>Refresh branding</button>
			<Draft />
		</>
	);
}
it("keeps the page draft mounted while refreshed branding loads", async () => {
	let finish!: (response: Response) => void;
	vi.stubGlobal(
		"fetch",
		vi
			.fn()
			.mockResolvedValueOnce(
				new Response(JSON.stringify({ application_name: "Before" })),
			)
			.mockImplementationOnce(
				() =>
					new Promise<Response>((resolve) => {
						finish = resolve;
					}),
			),
	);
	render(
		<OrgScopeProvider>
			<Shell />
		</OrgScopeProvider>,
	);
	const draft = await screen.findByRole("textbox", { name: "Draft" });
	fireEvent.change(draft, { target: { value: "Unsaved work" } });
	fireEvent.click(screen.getByRole("button", { name: "Refresh branding" }));
	expect(screen.getByRole("textbox", { name: "Draft" })).toHaveValue(
		"Unsaved work",
	);
	expect(screen.queryByText("Loading branding")).not.toBeInTheDocument();
	await act(async () =>
		finish(new Response(JSON.stringify({ application_name: "After" }))),
	);
	expect(await screen.findByText("After")).toBeInTheDocument();
	expect(screen.getByRole("textbox", { name: "Draft" })).toHaveValue(
		"Unsaved work",
	);
});
