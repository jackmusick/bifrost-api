import { act, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";
import { authFetch } from "@/lib/api-client";
import { ACCESS_TOKEN_KEY } from "@/lib/auth-token";

afterEach(() => {
	vi.unstubAllGlobals();
	localStorage.clear();
	sessionStorage.clear();
});

it("shares cookie recovery between provider bootstrap and an initial API request", async () => {
	const token = `header.${btoa(JSON.stringify({ sub: "account", email: "account@example.test", roles: ["authenticated"], exp: Math.floor(Date.now() / 1000) + 3600 }))}.signature`;
	let release!: () => void;
	const gate = new Promise<void>((resolve) => {
		release = resolve;
	});
	const refresh = vi.fn(async () => {
		await gate;
		return Response.json({ access_token: token });
	});
	vi.stubGlobal(
		"fetch",
		vi.fn(async (input: RequestInfo | URL) => {
			const url =
				typeof input === "string"
					? input
					: input instanceof URL
						? input.href
						: input.url;
			if (url.endsWith("/auth/status"))
				return Response.json({ needs_setup: false });
			if (url.endsWith("/api/auth/refresh")) return refresh();
			return Response.json({ ok: true });
		}),
	);
	function Probe() {
		const auth = useAuth();
		return (
			<p>
				{auth.isLoading
					? "Checking session"
					: (auth.user?.email ?? "Signed out")}
			</p>
		);
	}
	render(
		<MemoryRouter>
			<AuthProvider>
				<Probe />
			</AuthProvider>
		</MemoryRouter>,
	);
	await vi.waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
	const apiRequest = authFetch("/api/profile");
	await act(async () => {
		release();
		await apiRequest;
	});
	expect(refresh).toHaveBeenCalledTimes(1);
	expect(await screen.findByText("account@example.test")).toBeVisible();
	expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe(token);
});
