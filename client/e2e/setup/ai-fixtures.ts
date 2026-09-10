import type { BrowserContext } from "@playwright/test";

/** Suite-owned defaults live until test-stack reset, like the shared users.
 * Creating the first profile assigns required global defaults that cannot be
 * cleared through the API. Individual journey fixtures must not own that first
 * profile, otherwise their teardown cannot delete it.
 */
export async function seedLocalAIDefaults(context: BrowserContext) {
	const profiles = await context.request.get("/api/admin/ai/profiles");
	if (!profiles.ok())
		throw new Error(`List baseline AI profiles: ${profiles.status()}`);
	if ((await profiles.json()).length > 0) return;

	const csrf = (await context.cookies()).find(
		(cookie) => cookie.name === "csrf_token",
	);
	const headers: Record<string, string> = csrf
		? { "X-CSRF-Token": csrf.value }
		: {};
	const connectionResponse = await context.request.post(
		"/api/admin/ai/connections",
		{
			headers,
			data: {
				name: "E2E Local Provider",
				provider: "openai_compatible",
				api_key: "fixture-key",
				endpoint: "http://scheduler-fixtures:8080/v1",
			},
		},
	);
	if (!connectionResponse.ok())
		throw new Error(
			`Create baseline AI connection: ${connectionResponse.status()}`,
		);
	const connection = await connectionResponse.json();
	const profileResponse = await context.request.post(
		"/api/admin/ai/profiles",
		{
			headers,
			data: {
				name: "E2E Local Chat",
				connection_id: connection.id,
				model: "fixture-chat",
				enabled_for_chat: true,
				capabilities: {
					tool_calling: false,
					image_input: false,
					pdf_input: false,
					source: "manual",
				},
			},
		},
	);
	if (!profileResponse.ok())
		throw new Error(
			`Create baseline AI profile: ${profileResponse.status()}`,
		);
}
