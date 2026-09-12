import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { FormListSurface, type FormListItem } from "./FormListSurface";

const form = {
	id: "form-1",
	name: "Dispatch Intake",
	description: "Coordinate field work",
	is_active: true,
	organization_id: null,
	logo_url: null,
	logo_version: null,
} as FormListItem;

function validation(valid = true) {
	return new Map([
		[
			form.id,
			{
				valid,
				missingParams: valid ? [] : ["request_id"],
			},
		],
	]);
}

describe("FormListSurface", () => {
	it("opens the form runner from the grid card primary target", async () => {
		const onLaunch = vi.fn();
		const { user } = renderWithProviders(
			<FormListSurface
				forms={[form]}
				viewMode="grid"
				isPlatformAdmin
				canManageForms
				getOrgName={() => "Global"}
				formValidation={validation()}
				onLaunch={onLaunch}
			/>,
		);

		await user.click(
			screen.getByRole("button", { name: "Dispatch Intake" }),
		);

		expect(onLaunch).toHaveBeenCalledExactlyOnceWith(form);
	});

	it("keeps management overflow actions separate from grid launch", async () => {
		const onLaunch = vi.fn();
		const onEdit = vi.fn();
		const { user } = renderWithProviders(
			<FormListSurface
				forms={[form]}
				viewMode="grid"
				isPlatformAdmin
				canManageForms
				getOrgName={() => "Global"}
				formValidation={validation()}
				onLaunch={onLaunch}
				onEdit={onEdit}
			/>,
		);

		await user.click(
			screen.getByRole("button", { name: "Dispatch Intake actions" }),
		);
		await user.click(screen.getByRole("menuitem", { name: "Edit Form" }));

		expect(onEdit).toHaveBeenCalledExactlyOnceWith(form);
		expect(onLaunch).not.toHaveBeenCalled();
	});

	it("disables invalid grid cards while leaving admin actions available", async () => {
		const onLaunch = vi.fn();
		const onEdit = vi.fn();
		const { user } = renderWithProviders(
			<FormListSurface
				forms={[form]}
				viewMode="grid"
				isPlatformAdmin
				canManageForms
				getOrgName={() => "Global"}
				formValidation={validation(false)}
				onLaunch={onLaunch}
				onEdit={onEdit}
			/>,
		);

		expect(
			screen.getByRole("button", { name: "Dispatch Intake" }),
		).toBeDisabled();
		await user.click(
			screen.getByRole("button", { name: "Dispatch Intake actions" }),
		);
		await user.click(screen.getByRole("menuitem", { name: "Edit Form" }));

		expect(onLaunch).not.toHaveBeenCalled();
		expect(onEdit).toHaveBeenCalledExactlyOnceWith(form);
	});
});
