import { beforeEach, describe, expect, it, vi } from "vitest";

import { fireEvent, renderWithProviders, screen } from "@/test-utils";

const brandingApi = vi.hoisted(() => ({
	getBranding: vi.fn(),
	resetColor: vi.fn(),
	updateBranding: vi.fn(),
	uploadLogo: vi.fn(),
}));

vi.mock("@/hooks/useBranding", () => ({
	getBranding: brandingApi.getBranding,
	updateBranding: brandingApi.updateBranding,
	uploadLogo: brandingApi.uploadLogo,
	resetLogo: vi.fn(),
	resetColor: brandingApi.resetColor,
	resetApplicationName: vi.fn(),
}));

vi.mock("@/contexts/OrgScopeContext", () => ({
	useOrgScope: () => ({ refreshBranding: vi.fn() }),
}));

vi.mock("@/lib/branding", () => ({
	applyBrandingTheme: vi.fn(),
}));

vi.mock("sonner", () => ({
	toast: { success: vi.fn(), error: vi.fn() },
}));

import { createBrandPalette } from "@/lib/brand-palette";
import { Branding } from "./Branding";

function lightPreviewPrimaryAction() {
	return screen.getAllByText("Primary action")[0];
}

describe("Branding", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		brandingApi.getBranding.mockResolvedValue(null);
	});

	it("keeps the standard spacing between field labels and controls", async () => {
		renderWithProviders(<Branding />);

		const name = await screen.findByLabelText("Name");
		expect(name.parentElement).toHaveClass("space-y-2");
		expect(screen.getByLabelText("Color (Hex)").parentElement).toHaveClass(
			"space-y-2",
		);

		for (const input of screen.getAllByLabelText("Singular")) {
			expect(input.parentElement).toHaveClass("space-y-2");
		}
		for (const input of screen.getAllByLabelText("Plural")) {
			expect(input.parentElement).toHaveClass("space-y-2");
		}
	});

	it("shows a read error instead of blank branding controls when the initial load fails", async () => {
		brandingApi.getBranding.mockRejectedValueOnce(
			new Error("Synthetic failure"),
		);

		renderWithProviders(<Branding />);

		const alert = await screen.findByRole("alert");
		expect(alert).toHaveTextContent("Could not load branding settings.");
		expect(
			screen.getByRole("button", { name: "Retry branding settings" }),
		).toBeEnabled();
		expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
		expect(screen.queryByLabelText("Color (Hex)")).not.toBeInTheDocument();
	});

	it("keeps the editable default branding controls when the API returns no branding", async () => {
		renderWithProviders(<Branding />);

		const defaultPalette = createBrandPalette(null);

		expect(await screen.findByLabelText("Name")).toHaveValue("");
		expect(screen.getByLabelText("Color (Hex)")).toHaveValue(
			defaultPalette.light.primary,
		);
		expect(screen.getByLabelText("Color (Hex)")).toHaveAttribute(
			"placeholder",
			defaultPalette.light.primary,
		);
		expect(lightPreviewPrimaryAction()).toHaveStyle({
			backgroundColor: defaultPalette.light.primary,
			color: defaultPalette.light.primaryForeground,
		});
		expect(
			screen
				.getByLabelText("light theme activity gradient")
				.getAttribute("style"),
		).toContain(defaultPalette.light.activityGradient);
		expect(screen.queryByRole("alert")).not.toBeInTheDocument();
	});

	it("previews a loaded custom color with a custom activity gradient", async () => {
		brandingApi.getBranding.mockResolvedValueOnce({
			primary_color: "#3366ff",
			terminology: {
				app: { singular: "App", plural: "Apps" },
				agent: { singular: "Agent", plural: "Agents" },
				form: { singular: "Form", plural: "Forms" },
			},
		});

		renderWithProviders(<Branding />);

		const customPalette = createBrandPalette("#3366ff");

		expect(await screen.findByLabelText("Color (Hex)")).toHaveValue(
			"#3366ff",
		);
		expect(lightPreviewPrimaryAction()).toHaveStyle({
			backgroundColor: customPalette.light.primary,
			color: customPalette.light.primaryForeground,
		});
		expect(
			screen
				.getByLabelText("light theme activity gradient")
				.getAttribute("style"),
		).toContain(customPalette.light.activityGradient);
	});

	it("keeps the persisted reset in the default preview state when color resets to null", async () => {
		brandingApi.getBranding.mockResolvedValueOnce({
			primary_color: "#3366ff",
			terminology: {
				app: { singular: "App", plural: "Apps" },
				agent: { singular: "Agent", plural: "Agents" },
				form: { singular: "Form", plural: "Forms" },
			},
		});
		brandingApi.resetColor.mockResolvedValueOnce({
			primary_color: null,
			terminology: {
				app: { singular: "App", plural: "Apps" },
				agent: { singular: "Agent", plural: "Agents" },
				form: { singular: "Form", plural: "Forms" },
			},
		});

		const { user } = renderWithProviders(<Branding />);

		await screen.findByDisplayValue("#3366ff");
		await user.click(
			screen.getByRole("button", { name: "Reset to default color" }),
		);

		const defaultPalette = createBrandPalette(null);
		expect(brandingApi.resetColor).toHaveBeenCalledOnce();
		expect(screen.getByLabelText("Color (Hex)")).toHaveValue(
			defaultPalette.light.primary,
		);
		expect(lightPreviewPrimaryAction()).toHaveStyle({
			backgroundColor: defaultPalette.light.primary,
			color: defaultPalette.light.primaryForeground,
		});
	});

	it("does not persist the shown default color when saving terminology from default branding", async () => {
		brandingApi.updateBranding.mockResolvedValueOnce({
			primary_color: null,
			terminology: {
				app: { singular: "Game", plural: "Games" },
				agent: { singular: "Agent", plural: "Agents" },
				form: { singular: "Form", plural: "Forms" },
			},
		});

		const { user } = renderWithProviders(<Branding />);

		await screen.findByDisplayValue(createBrandPalette(null).light.primary);
		const appSingular = document.getElementById("app-singular");
		fireEvent.change(appSingular!, { target: { value: "Game" } });
		await user.click(
			screen.getByRole("button", { name: "Update Terminology" }),
		);

		expect(brandingApi.updateBranding).toHaveBeenCalledWith({
			terminology: {
				app: { singular: "Game", plural: "Apps" },
				agent: { singular: "Agent", plural: "Agents" },
				form: { singular: "Form", plural: "Forms" },
			},
		});
	});

	it("preserves default color semantics when saving terminology after a color reset", async () => {
		brandingApi.getBranding.mockResolvedValueOnce({
			primary_color: "#3366ff",
			terminology: {
				app: { singular: "App", plural: "Apps" },
				agent: { singular: "Agent", plural: "Agents" },
				form: { singular: "Form", plural: "Forms" },
			},
		});
		brandingApi.resetColor.mockResolvedValueOnce({
			primary_color: null,
			terminology: {
				app: { singular: "App", plural: "Apps" },
				agent: { singular: "Agent", plural: "Agents" },
				form: { singular: "Form", plural: "Forms" },
			},
		});
		brandingApi.updateBranding.mockResolvedValueOnce({
			primary_color: null,
			terminology: {
				app: { singular: "Game", plural: "Apps" },
				agent: { singular: "Agent", plural: "Agents" },
				form: { singular: "Form", plural: "Forms" },
			},
		});

		const { user } = renderWithProviders(<Branding />);

		await screen.findByDisplayValue("#3366ff");
		await user.click(
			screen.getByRole("button", { name: "Reset to default color" }),
		);
		const appSingular = document.getElementById("app-singular");
		fireEvent.change(appSingular!, { target: { value: "Game" } });
		await user.click(
			screen.getByRole("button", { name: "Update Terminology" }),
		);

		expect(brandingApi.updateBranding).toHaveBeenCalledWith({
			terminology: {
				app: { singular: "Game", plural: "Apps" },
				agent: { singular: "Agent", plural: "Agents" },
				form: { singular: "Form", plural: "Forms" },
			},
		});
	});

	it("preserves loaded branding and disables saves when a refresh fails", async () => {
		brandingApi.getBranding
			.mockResolvedValueOnce({
				application_name: "Northwind",
				primary_color: "#123456",
				terminology: {
					app: { singular: "App", plural: "Apps" },
					agent: { singular: "Agent", plural: "Agents" },
					form: { singular: "Form", plural: "Forms" },
				},
			})
			.mockRejectedValueOnce(new Error("Synthetic refresh failure"));
		brandingApi.uploadLogo.mockResolvedValue(undefined);

		const { user } = renderWithProviders(<Branding />);

		const name = await screen.findByLabelText("Name");
		await user.clear(name);
		await user.type(name, "Draft Name");

		const fileInput = document.getElementById(
			"squareLogoInput",
		) as HTMLInputElement;
		await user.upload(
			fileInput,
			new File(["synthetic"], "logo.png", { type: "image/png" }),
		);

		const alert = await screen.findByRole("alert");
		expect(alert).toHaveTextContent("Could not refresh branding settings.");
		expect(screen.getByLabelText("Name")).toHaveValue("Draft Name");
		expect(screen.getByLabelText("Color (Hex)")).toHaveValue("#123456");
		expect(
			screen.getByRole("button", { name: "Update Name" }),
		).toBeDisabled();
		expect(
			screen.getByRole("button", { name: "Update Color" }),
		).toBeDisabled();
		expect(
			screen.getByRole("button", { name: "Update Terminology" }),
		).toBeDisabled();
	});
});
