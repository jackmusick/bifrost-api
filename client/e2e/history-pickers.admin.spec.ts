import { test, expect } from "./fixtures/api-fixture";

test("History search pickers expand beyond compact triggers and fit mobile", async ({
	page,
}) => {
	for (const width of [1440, 390]) {
		await page.setViewportSize({ width, height: 1000 });
		await page.goto("/history");
		if (width < 1024)
			await page
				.getByRole("button", { name: "Show filters", exact: true })
				.click();
		for (const [name, search] of [
			["All workflows", "Search workflows"],
			["Organization scope", "Search organizations"],
		]) {
			const trigger = page.getByRole("combobox", { name, exact: true });
			await trigger.click();
			const input = page.getByRole("combobox", {
				name: search,
				exact: true,
			});
			await expect(input).toBeVisible();
			const popup = page.getByRole("dialog");
			await expect
				.poll(async () => {
					const box = await popup.boundingBox();
					return (
						box !== null &&
						box.width >= Math.min(320, width - 32) &&
						box.x >= 0 &&
						box.x + box.width <= width
					);
				})
				.toBe(true);
			if (width === 1440) {
				const triggerBox = await trigger.boundingBox();
				const popupBox = await popup.boundingBox();
				expect(popupBox!.width).toBeGreaterThan(triggerBox!.width);
			}
			await input.fill("no matching resource for layout check");
			await expect(
				page.getByText(
					search === "Search workflows"
						? "No workflows found."
						: "No organizations found.",
					{ exact: true },
				),
			).toBeVisible();
			await page.keyboard.press("Escape");
			await expect(input).not.toBeVisible();
		}
	}
});
