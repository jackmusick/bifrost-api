import { generateUUID } from "./uuid";

/** Generate a client message ID, retaining the legacy non-UUID fallback without Web Crypto. */
export function generateMessageId(): string {
	if (
		typeof globalThis.crypto?.randomUUID === "function" ||
		typeof globalThis.crypto?.getRandomValues === "function"
	)
		return generateUUID();
	return `fallback-${Date.now().toString(36)}-${Math.random()
		.toString(36)
		.slice(2, 10)}`;
}
