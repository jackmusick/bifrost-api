import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import { FormLogoEditor } from "./FormLogoEditor";

const mockBumpEntityLogo = vi.fn();
let logoDropZoneOnChange: (() => void) | undefined;

vi.mock("@/components/LogoDropZone", () => ({
	LogoDropZone: ({
		onChange,
		previewUrl,
	}: {
		onChange?: () => void;
		previewUrl: string;
	}) => {
		logoDropZoneOnChange = onChange;
		return <div data-testid="logo-drop-zone">{previewUrl}</div>;
	},
}));

vi.mock("@/components/entityLogoVersions", async (importOriginal) => {
	const actual =
		await importOriginal<typeof import("@/components/entityLogoVersions")>();
	return {
		...actual,
		bumpEntityLogo: (...args: unknown[]) => mockBumpEntityLogo(...args),
	};
});

function renderEditor(queryClient = new QueryClient()) {
	return render(
		<QueryClientProvider client={queryClient}>
			<FormLogoEditor formId="form-1" logoUrl="/api/forms/form-1/logo" />
		</QueryClientProvider>,
	);
}

describe("FormLogoEditor", () => {
	it("opens the upload dialog with the current form logo preview", async () => {
		renderEditor();

		await screen.getByRole("button", { name: "Edit form logo" }).click();

		expect(screen.getByTestId("logo-drop-zone")).toHaveTextContent(
			"/api/forms/form-1/logo",
		);
	});

	it("bumps the form logo and invalidates form and Home queries after changes", async () => {
		const queryClient = new QueryClient();
		const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
		renderEditor(queryClient);

		await screen.getByRole("button", { name: "Edit form logo" }).click();
		logoDropZoneOnChange?.();

		expect(mockBumpEntityLogo).toHaveBeenCalledWith("form", "form-1");
		expect(invalidateQueries).toHaveBeenCalledWith({
			queryKey: ["get", "/api/forms"],
		});
		expect(invalidateQueries).toHaveBeenCalledWith({
			queryKey: [
				"get",
				"/api/forms/{form_id}",
				{ params: { path: { form_id: "form-1" } } },
			],
		});
		expect(invalidateQueries).toHaveBeenCalledWith({
			queryKey: ["get", "/api/home"],
		});
	});
});
