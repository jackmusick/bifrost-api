import { expect, it } from "vitest";
import { isEntityManaged, normalizeEntities, type FormPublic } from "./types";
it("preserves form scope, access and creation date and recognizes solution ownership", () => {
	const form = {
		id: "form",
		name: "Scoped form",
		is_active: true,
		organization_id: "org",
		access_level: "authenticated",
		created_at: "2026-01-01T00:00:00Z",
		is_solution_managed: true,
		solution_id: "solution",
	} as FormPublic;
	const [entity] = normalizeEntities([], [form]);
	expect(entity).toMatchObject({
		organizationId: "org",
		accessLevel: "authenticated",
		createdAt: form.created_at,
	});
	expect(isEntityManaged(entity)).toBe(true);
	expect(
		isEntityManaged({
			...entity,
			original: { ...form, is_solution_managed: false },
		}),
	).toBe(true);
	expect(
		isEntityManaged({
			...entity,
			original: {
				...form,
				is_solution_managed: false,
				solution_id: null,
			},
		}),
	).toBe(false);
});
