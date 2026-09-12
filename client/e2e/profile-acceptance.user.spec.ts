import { test, expect, type AuthedApi } from "./fixtures/api-fixture";

const UNIQUE = `${Date.now()}_${Math.floor(Math.random() * 10_000)}`;
const UPDATED_NAME = `PROFILE-01 Member ${UNIQUE}`;

type ProfileResponse = {
	id: string;
	email: string;
	name: string | null;
	has_avatar: boolean;
	has_password: boolean;
	organization_id: string | null;
	is_superuser: boolean;
};

async function expectOk(
	response: Pick<Awaited<ReturnType<AuthedApi["get"]>>, "ok" | "text">,
) {
	expect(response.ok(), await response.text()).toBe(true);
}

async function readProfile(api: AuthedApi) {
	const response = await api.get("/api/profile");
	await expectOk(response);
	return (await response.json()) as ProfileResponse;
}

async function updateProfileName(api: AuthedApi, name: string) {
	const response = await api.patch("/api/profile", {
		data: { name },
	});
	await expectOk(response);
	return (await response.json()) as ProfileResponse;
}

test.describe("Profile acceptance", () => {
	let originalName: string;
	let capturedOriginalName = false;

	test.beforeEach(async ({ api }) => {
		const profile = await readProfile(api);
		if (typeof profile.name !== "string" || !profile.name.trim()) {
			throw new Error(
				"PROFILE-01 requires the seeded member to have a name",
			);
		}
		originalName = profile.name;
		capturedOriginalName = true;
	});

	test.afterEach(async ({ api }) => {
		if (capturedOriginalName) {
			await updateProfileName(api, originalName);
		}
		capturedOriginalName = false;
	});

	test("PROFILE-01 member edits display name and reloads saved profile", async ({
		page,
		api,
	}, testInfo) => {
		await page.goto("/user-settings/basic-info");
		await expect(
			page.getByRole("heading", { name: "User Settings" }),
		).toBeVisible();

		const nameInput = page.getByLabel("Name", { exact: true });
		await expect(nameInput).toHaveValue(originalName);
		await nameInput.fill(UPDATED_NAME);

		const saveResponse = page.waitForResponse(
			(response) =>
				response.url().includes("/api/profile") &&
				response.request().method() === "PATCH",
		);
		await page.getByRole("button", { name: "Save Changes" }).click();

		await expectOk(await saveResponse);
		await expect(
			page.getByRole("button", { name: "Saved" }),
		).toBeDisabled();
		await expect(nameInput).toHaveValue(UPDATED_NAME);
		await expect
			.poll(async () => (await readProfile(api)).name)
			.toBe(UPDATED_NAME);

		await page.reload();
		await expect(
			page.getByRole("heading", { name: "User Settings" }),
		).toBeVisible();
		await expect(page.getByLabel("Name", { exact: true })).toHaveValue(
			UPDATED_NAME,
		);
		await expect(
			page.getByRole("button", { name: "Saved" }),
		).toBeDisabled();

		await testInfo.attach("PROFILE-01 saved and reloaded basic info", {
			body: await page.screenshot({ fullPage: true }),
			contentType: "image/png",
		});
	});
});
