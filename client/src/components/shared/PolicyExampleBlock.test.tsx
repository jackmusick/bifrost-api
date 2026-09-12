import {
	render,
	screen,
	fireEvent,
	waitFor,
	act,
} from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

// Monaco → textarea labelled by `path`.
vi.mock("@monaco-editor/react", () => ({
	default: ({ value, path }: { value?: string; path?: string }) => (
		<textarea
			aria-label={path ?? "monaco-editor"}
			value={value ?? ""}
			readOnly
		/>
	),
}));
vi.mock("@/contexts/ThemeContext", () => ({
	useTheme: () => ({ theme: "light" }),
}));

import { PolicyExampleBlock } from "./PolicyExampleBlock";

const POLICY = { policies: [{ name: "admin_bypass", actions: ["read"] }] };

describe("PolicyExampleBlock", () => {
	it("defaults to YAML and toggles to JSON", () => {
		render(
			<PolicyExampleBlock
				heading="admin_bypass"
				description="desc"
				policy={POLICY}
				index={0}
			/>,
		);
		// YAML is the default view.
		const yamlEditor = screen.getByLabelText(
			"example-0.yaml",
		) as HTMLTextAreaElement;
		expect(yamlEditor).toBeInTheDocument();
		expect(yamlEditor.value).toMatch(/policies:/);
		expect(yamlEditor.value).not.toMatch(/^\{/);

		fireEvent.click(screen.getByRole("button", { name: /^json$/i }));
		const jsonEditor = screen.getByLabelText(
			"example-0.json",
		) as HTMLTextAreaElement;
		expect(JSON.parse(jsonEditor.value)).toHaveProperty("policies");
	});

	it("copies the currently-shown format", async () => {
		const writeText = vi.fn().mockResolvedValue(undefined);
		Object.defineProperty(navigator, "clipboard", {
			value: { writeText },
			configurable: true,
		});
		render(
			<PolicyExampleBlock
				heading="admin_bypass"
				description="desc"
				policy={POLICY}
				index={1}
			/>,
		);
		fireEvent.click(screen.getByRole("button", { name: /^copy /i }));
		expect(writeText).toHaveBeenCalledWith(
			expect.stringContaining("policies:"),
		);
		await screen.findByText("Copied!");
		fireEvent.click(screen.getByRole("button", { name: "JSON" }));
		fireEvent.click(
			screen.getByRole("button", { name: "Copy admin_bypass as JSON" }),
		);
		await waitFor(() =>
			expect(writeText).toHaveBeenLastCalledWith(
				JSON.stringify(POLICY, null, 2),
			),
		);
		await screen.findByText("Copied!");
	});
	it("waits for clipboard confirmation and recovers from a rejected write", async () => {
		let rejectWrite: (reason: Error) => void = () => {};
		const writeText = vi
			.fn()
			.mockImplementationOnce(
				() =>
					new Promise((_, reject) => {
						rejectWrite = reject;
					}),
			)
			.mockResolvedValue(undefined);
		Object.defineProperty(navigator, "clipboard", {
			value: { writeText },
			configurable: true,
		});
		render(
			<PolicyExampleBlock
				heading="admin_bypass"
				description="desc"
				policy={POLICY}
				index={2}
			/>,
		);
		const copy = screen.getByRole("button", {
			name: "Copy admin_bypass as YAML",
		});
		fireEvent.click(copy);
		expect(copy).toBeDisabled();
		expect(copy).toHaveTextContent("Copying…");
		expect(screen.queryByText("Copied!")).not.toBeInTheDocument();
		await act(async () => rejectWrite(new Error("Denied")));
		expect(screen.getByRole("alert")).toHaveTextContent("Could not copy");
		expect(copy).toBeEnabled();
		fireEvent.click(copy);
		await screen.findByText("Copied!");
		expect(screen.queryByRole("alert")).not.toBeInTheDocument();
		expect(screen.getByRole("status")).toHaveTextContent(
			"YAML copied to clipboard.",
		);
	});

	it("does not report success when the clipboard API is unavailable", async () => {
		Object.defineProperty(navigator, "clipboard", {
			value: undefined,
			configurable: true,
		});
		render(
			<PolicyExampleBlock
				heading="example"
				description="desc"
				policy={POLICY}
				index={3}
			/>,
		);
		fireEvent.click(
			screen.getByRole("button", { name: "Copy example as YAML" }),
		);
		expect(await screen.findByRole("alert")).toHaveTextContent(
			"Could not copy",
		);
		expect(screen.queryByText("Copied!")).not.toBeInTheDocument();
	});
});
