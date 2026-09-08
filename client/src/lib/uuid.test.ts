import { afterEach, expect, it, vi } from "vitest";
import { generateUUID } from "./uuid";
afterEach(() => vi.unstubAllGlobals());
it("generates UUID v4 correlation IDs with getRandomValues on private HTTP origins", () => {
	const getRandomValues = vi.fn((bytes: Uint8Array) => {
		bytes.fill(255);
		return bytes;
	});
	vi.stubGlobal("crypto", { getRandomValues });
	expect(generateUUID()).toBe("ffffffff-ffff-4fff-bfff-ffffffffffff");
	expect(getRandomValues).toHaveBeenCalledTimes(1);
});
it("never sends a non-UUID job identifier when cryptographic randomness is absent", () => {
	vi.stubGlobal("crypto", undefined);
	expect(() => generateUUID()).toThrow(
		"Browser cryptographic randomness is unavailable.",
	);
});
