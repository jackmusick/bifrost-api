import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";

import {
	act,
	fireEvent,
	renderWithProviders,
	screen,
	waitFor,
} from "@/test-utils";

const authFetch = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ authFetch }));

import { ModelCapabilityEditor } from "./ModelCapabilityEditor";

function deferred<T>() {
	let resolve!: (value: T) => void;
	let reject!: (reason?: unknown) => void;
	const promise = new Promise<T>((res, rej) => {
		resolve = res;
		reject = rej;
	});
	return { promise, resolve, reject };
}

function capabilitiesResponse(overrides: Record<string, unknown> = {}) {
	return new Response(
		JSON.stringify({
			capabilities: {
				image_input: false,
				pdf_input: false,
				tool_calling: false,
				source: "verified",
				fingerprint: "verified-target",
				...overrides,
			},
			message: "Provider conformance check completed.",
		}),
		{ status: 200 },
	);
}

beforeEach(() => {
	authFetch.mockReset();
});

afterEach(() => {
	vi.useRealTimers();
});

describe("ModelCapabilityEditor", () => {
	it("runs provider verification for an unknown model and returns the result", async () => {
		authFetch.mockResolvedValueOnce(
			capabilitiesResponse({
				image_input: true,
				pdf_input: true,
				tool_calling: true,
				fingerprint: "verified-target",
			}),
		);
		const onChange = vi.fn();
		const { user } = renderWithProviders(
			<ModelCapabilityEditor
				provider="openai"
				model="private-model"
				endpoint="https://models.example.test/v1"
				apiKey="new-key"
				value={null}
				onChange={onChange}
			/>,
		);

		await user.click(
			screen.getByRole("button", { name: /verify with provider/i }),
		);

		await waitFor(() => expect(onChange).toHaveBeenCalledTimes(1));
		expect(authFetch).toHaveBeenCalledWith(
			"/api/admin/llm/model-capabilities/verify",
			expect.objectContaining({
				method: "POST",
				body: expect.stringContaining('"api_key":"new-key"'),
			}),
		);
	});

	it("succeeds inside React.StrictMode", async () => {
		authFetch.mockResolvedValueOnce(capabilitiesResponse());
		const onChange = vi.fn();
		const { user } = renderWithProviders(
			<StrictMode>
				<ModelCapabilityEditor
					provider="openai"
					model="private-model"
					endpoint="https://models.example.test/v1"
					apiKey="new-key"
					value={null}
					onChange={onChange}
				/>
			</StrictMode>,
		);

		await user.click(
			screen.getByRole("button", { name: /verify with provider/i }),
		);

		await waitFor(() => expect(onChange).toHaveBeenCalledTimes(1));
		expect(onChange).toHaveBeenCalledWith(
			expect.objectContaining({ source: "verified" }),
		);
	});

	it("records an administrator override as manual", async () => {
		const onChange = vi.fn();
		const { user } = renderWithProviders(
			<ModelCapabilityEditor
				provider="openai"
				model="private-model"
				endpoint=""
				value={null}
				onChange={onChange}
			/>,
		);

		await user.click(
			screen.getByRole("button", {
				name: "Tool Calling: Not Verified",
			}),
		);
		expect(onChange).toHaveBeenCalledWith(
			expect.objectContaining({ tool_calling: true, source: "manual" }),
		);
	});

	it("shows supported and unsupported capabilities as labeled touch controls", async () => {
		const capabilities = {
			image_input: false,
			pdf_input: false,
			tool_calling: true,
			source: "openrouter" as const,
			fingerprint: "catalog-target",
		};
		const { user } = renderWithProviders(
			<ModelCapabilityEditor
				provider="openai"
				model="deepseek/deepseek-v4-pro"
				endpoint="https://openrouter.ai/api/v1"
				value={capabilities}
				onChange={vi.fn()}
			/>,
		);

		expect(
			screen.getByRole("button", {
				name: "Image Input: Not Supported",
			}),
		).toHaveClass("text-[var(--bf-danger)]");
		expect(
			screen.getByRole("button", {
				name: "Tool Calling: Supported",
			}),
		).toHaveClass("text-[var(--bf-success)]");
		expect(
			screen.getByRole("button", {
				name: "Tool Calling: Supported",
			}),
		).toHaveClass("min-h-11");
		expect(
			screen
				.getByRole("button", {
					name: "Tool Calling: Supported",
				})
				.querySelector("svg"),
		).toHaveClass("size-4");
		expect(screen.queryByRole("switch")).not.toBeInTheDocument();
		expect(screen.queryByText("Capabilities")).not.toBeInTheDocument();
		expect(screen.getByText("OpenRouter")).toBeInTheDocument();
		expect(
			screen.getByRole("button", {
				name: "Refresh Model Capabilities",
			}),
		).toContainElement(screen.getByText("OpenRouter"));
		expect(
			screen.queryByText(/native image generation/i),
		).not.toBeInTheDocument();

		await user.hover(
			screen.getByRole("button", {
				name: "Tool Calling: Supported",
			}),
		);
		expect(
			await screen.findByText("Supported · OpenRouter"),
		).toBeInTheDocument();
	});

	it("refreshes through the source status and replaces its check with a spinner", async () => {
		let resolveLookup: ((response: Response) => void) | undefined;
		authFetch.mockImplementation(
			() =>
				new Promise<Response>((resolve) => {
					resolveLookup = resolve;
				}),
		);
		const capabilities = {
			image_input: false,
			pdf_input: false,
			tool_calling: true,
			source: "openrouter" as const,
			fingerprint: "catalog-target",
		};
		const onChange = vi.fn();
		const { user } = renderWithProviders(
			<ModelCapabilityEditor
				provider="openai"
				model="deepseek/deepseek-v4-pro"
				endpoint="https://openrouter.ai/api/v1"
				value={capabilities}
				onChange={onChange}
			/>,
		);
		const refresh = screen.getByRole("button", {
			name: "Refresh Model Capabilities",
		});

		await user.click(refresh);
		expect(
			refresh.querySelector('[class*="motion-safe:animate-spin"]'),
		).toBeInTheDocument();
		expect(refresh).toHaveTextContent("OpenRouter");

		resolveLookup?.(
			new Response(
				JSON.stringify({
					capabilities,
					message: "Catalog refreshed.",
				}),
				{ status: 200 },
			),
		);
		await waitFor(() =>
			expect(onChange).toHaveBeenCalledWith(capabilities),
		);
	});

	it("ignores a stale detection result after the model changes and a manual override lands", async () => {
		const first = deferred<Response>();
		authFetch.mockImplementation(() => first.promise);
		const onChange = vi.fn();
		const user = userEvent.setup();
		const { rerender } = renderWithProviders(
			<ModelCapabilityEditor
				provider="openai"
				model="private-model-a"
				endpoint="https://models.example.test/v1"
				apiKey="key-a"
				value={null}
				onChange={onChange}
			/>,
		);

		rerender(
			<ModelCapabilityEditor
				provider="openai"
				model="private-model-b"
				endpoint="https://models.example.test/v1"
				apiKey="key-a"
				value={null}
				onChange={onChange}
			/>,
		);
		await waitFor(() => expect(authFetch).toHaveBeenCalledTimes(1));

		await user.click(
			screen.getByRole("button", {
				name: "Tool Calling: Not Verified",
			}),
		);
		expect(onChange).toHaveBeenCalledWith(
			expect.objectContaining({ tool_calling: true, source: "manual" }),
		);

		await act(async () => {
			first.resolve(capabilitiesResponse({ tool_calling: true }));
			await Promise.resolve();
		});

		expect(onChange).toHaveBeenCalledTimes(1);
	});

	it("ignores a pending verification result after the endpoint changes", async () => {
		const pending = deferred<Response>();
		authFetch.mockImplementation(() => pending.promise);
		const onChange = vi.fn();
		const user = userEvent.setup();
		const { rerender } = renderWithProviders(
			<ModelCapabilityEditor
				provider="openai"
				model="private-model"
				endpoint="https://models.example.test/v1"
				apiKey="key-a"
				value={null}
				onChange={onChange}
			/>,
		);

		await user.click(
			screen.getByRole("button", { name: /verify with provider/i }),
		);
		expect(authFetch).toHaveBeenCalledTimes(1);

		rerender(
			<ModelCapabilityEditor
				provider="openai"
				model="private-model"
				endpoint="https://models.example.test/v2"
				apiKey="key-a"
				value={null}
				onChange={onChange}
			/>,
		);

		await act(async () => {
			pending.resolve(capabilitiesResponse());
			await Promise.resolve();
		});

		expect(onChange).not.toHaveBeenCalled();
	});

	it("ignores a pending verification result after unmount", async () => {
		const pending = deferred<Response>();
		authFetch.mockImplementation(() => pending.promise);
		const onChange = vi.fn();
		const user = userEvent.setup();
		const { unmount } = renderWithProviders(
			<ModelCapabilityEditor
				provider="openai"
				model="private-model"
				endpoint="https://models.example.test/v1"
				apiKey="key-a"
				value={null}
				onChange={onChange}
			/>,
		);

		await user.click(
			screen.getByRole("button", { name: /verify with provider/i }),
		);
		expect(authFetch).toHaveBeenCalledTimes(1);
		unmount();

		await act(async () => {
			pending.resolve(capabilitiesResponse());
			await Promise.resolve();
		});

		expect(onChange).not.toHaveBeenCalled();
	});

	it("blocks duplicate current verification requests", async () => {
		const pending = deferred<Response>();
		authFetch.mockImplementation(() => pending.promise);
		const onChange = vi.fn();
		const user = userEvent.setup();
		renderWithProviders(
			<ModelCapabilityEditor
				provider="openai"
				model="private-model"
				endpoint="https://models.example.test/v1"
				apiKey="key-a"
				value={null}
				onChange={onChange}
			/>,
		);

		await user.click(
			screen.getByRole("button", { name: /verify with provider/i }),
		);
		await user.click(
			screen.getByRole("button", { name: /verify with provider/i }),
		);

		expect(authFetch).toHaveBeenCalledTimes(1);
		await act(async () => {
			pending.resolve(capabilitiesResponse());
			await Promise.resolve();
		});
		expect(onChange).toHaveBeenCalledTimes(1);
	});
	it("keeps a manual edit made before automatic detection starts", async () => {
		vi.useFakeTimers();

		const onChange = vi.fn();
		const props = {
			provider: "openai" as const,
			endpoint: "",
			value: null,
			onChange,
		};
		const { rerender } = renderWithProviders(
			<ModelCapabilityEditor {...props} model="first" />,
		);
		rerender(<ModelCapabilityEditor {...props} model="second" />);
		fireEvent.click(
			screen.getByRole("button", { name: "Tool Calling: Not Verified" }),
		);
		await act(async () => {
			vi.advanceTimersByTime(450);
		});
		expect(authFetch).not.toHaveBeenCalled();
		expect(onChange).toHaveBeenCalledExactlyOnceWith(
			expect.objectContaining({ tool_calling: true, source: "manual" }),
		);
	});
});
