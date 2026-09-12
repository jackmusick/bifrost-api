import { describe, expect, it } from "vitest";

import { routeRevealKey } from "./route-reveal-key";

describe("routeRevealKey", () => {
	it("preserves only the new-conversation draft transition", () => {
		expect(
			routeRevealKey("/chat/new-id", { preserveChatDraft: true }),
		).toBe("/chat");
		expect(routeRevealKey("/chat/other-id")).toBe("/chat/other-id");
		expect(
			routeRevealKey("/chat/artifacts", { preserveChatDraft: true }),
		).toBe("/chat/artifacts");
		expect(routeRevealKey("/agents", { preserveChatDraft: true })).toBe(
			"/agents",
		);
	});
	it("keeps account tab focus across subsection navigation", () => {
		expect(routeRevealKey("/user-settings/security")).toBe("user-settings");
		expect(routeRevealKey("/user-settings/preferences")).toBe(
			"user-settings",
		);
	});
	it("keeps the Settings shell mounted across subsection navigation", () => {
		expect(routeRevealKey("/settings/ai")).toBe("settings");
		expect(routeRevealKey("/settings/github")).toBe("settings");
	});

	it("keeps app runners mounted and keys ordinary pages by pathname", () => {
		expect(routeRevealKey("/apps/example/preview")).toBe("app-runner");
		expect(routeRevealKey("/apps/example/edit/code")).toBe(
			"/apps/example/edit/code",
		);
		expect(routeRevealKey("/apps/example/edit")).toBe("/apps/example/edit");
		expect(routeRevealKey("/agents")).toBe("/agents");
	});
});
