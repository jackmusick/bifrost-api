import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";

import { renderWithProviders } from "@/test-utils";
import { WorkflowKeys } from "./WorkflowKeys";

const workflowKeysApi = vi.hoisted(() => ({
	useWorkflowKeys: vi.fn(),
	useCreateWorkflowKey: vi.fn(),
	useRevokeWorkflowKey: vi.fn(),
	useWorkflowsMetadata: vi.fn(),
}));

vi.mock("framer-motion", () => ({
	useReducedMotion: () => false,
}));

vi.mock("@/hooks/useWorkflowKeys", () => ({
	useWorkflowKeys: (...args: unknown[]) => workflowKeysApi.useWorkflowKeys(...args),
	useCreateWorkflowKey: (...args: unknown[]) =>
		workflowKeysApi.useCreateWorkflowKey(...args),
	useRevokeWorkflowKey: (...args: unknown[]) =>
		workflowKeysApi.useRevokeWorkflowKey(...args),
}));

vi.mock("@/hooks/useWorkflows", () => ({
	useWorkflowsMetadata: (...args: unknown[]) =>
		workflowKeysApi.useWorkflowsMetadata(...args),
}));

function makeKey(overrides: Record<string, unknown> = {}) {
	return {
		id: "key-1",
		masked_key: "****1111",
		raw_key: "raw-secret-key",
		description: "Primary API key",
		workflow_id: "workflow-1",
		workflow_name: "Workflow One",
		created_at: "2026-09-07T12:00:00.000Z",
		expires_at: null,
		last_used_at: null,
		...overrides,
	};
}

function makeWorkflow(overrides: Record<string, unknown> = {}) {
	return {
		id: "workflow-1",
		name: "Workflow One",
		endpoint_enabled: true,
		public_endpoint: false,
		...overrides,
	};
}

beforeEach(() => {
	vi.restoreAllMocks();
	workflowKeysApi.useCreateWorkflowKey.mockReturnValue({
		mutateAsync: vi.fn(),
	});
	workflowKeysApi.useRevokeWorkflowKey.mockReturnValue({
		mutateAsync: vi.fn(),
	});
});

describe("WorkflowKeys", () => {
	it("keeps cached keys visible when the key refresh fails", () => {
		const refetchKeys = vi.fn();
		const refetchWorkflows = vi.fn();

		workflowKeysApi.useWorkflowKeys.mockReturnValue({
			data: [makeKey()],
			isLoading: false,
			isFetching: false,
			isError: true,
			refetch: refetchKeys,
		});
		workflowKeysApi.useWorkflowsMetadata.mockReturnValue({
			data: { workflows: [makeWorkflow()] },
			isLoading: false,
			isFetching: false,
			hasData: true,
			isError: false,
			refetch: refetchWorkflows,
		});

		renderWithProviders(<WorkflowKeys />);

		expect(screen.getByTestId("workflow-key-key-1")).toBeInTheDocument();
		expect(
			screen.getByText(/could not refresh workflow keys/i),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /retry workflow keys/i }),
		).toBeEnabled();
		expect(
			screen.getByRole("button", { name: /create api key/i }),
		).toBeDisabled();
		expect(screen.queryByText(/no api keys found/i)).not.toBeInTheDocument();
	});

	it("keeps cached rows visible when metadata refresh fails and does not mark unknown workflows as orphaned", () => {
		const refetchKeys = vi.fn();
		const refetchWorkflows = vi.fn();

		workflowKeysApi.useWorkflowKeys.mockReturnValue({
			data: [
				makeKey({
					workflow_id: "workflow-missing",
					workflow_name: undefined,
				}),
			],
			isLoading: false,
			isFetching: false,
			isError: false,
			refetch: refetchKeys,
		});
		workflowKeysApi.useWorkflowsMetadata.mockReturnValue({
			data: { workflows: [makeWorkflow()] },
			isLoading: false,
			isFetching: false,
			hasData: true,
			isError: true,
			refetch: refetchWorkflows,
		});

		renderWithProviders(<WorkflowKeys />);

		expect(screen.getByTestId("workflow-key-key-1")).toBeInTheDocument();
		expect(screen.getByText(/workflow unavailable/i)).toBeInTheDocument();
		expect(
			screen.getByText(/could not refresh workflow metadata/i),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /retry workflow metadata/i }),
		).toBeEnabled();
		expect(
			screen.getByRole("button", { name: /create api key/i }),
		).toBeDisabled();
		expect(
			screen.queryByText(/workflow no longer exists/i),
		).not.toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /revoke key \*\*\*\*1111/i }),
		).toBeDisabled();
	});
});
