import { act } from "@testing-library/react";
import { renderWithProviders } from "@/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockInvalidateQueries = vi.fn();

vi.mock("@tanstack/react-query", async () => {
	const actual = await vi.importActual<typeof import("@tanstack/react-query")>(
		"@tanstack/react-query",
	);
	return {
		...actual,
		useQueryClient: () => ({ invalidateQueries: mockInvalidateQueries }),
	};
});

import { OrgScopeQueryInvalidator } from "./OrgScopeQueryInvalidator";
import { useScopeStore } from "@/stores/scopeStore";

beforeEach(() => {
	mockInvalidateQueries.mockReset();
	useScopeStore.setState({
		scope: { type: "global", orgId: null, orgName: null },
		isGlobalScope: true,
		_hasHydrated: true,
	});
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("OrgScopeQueryInvalidator", () => {
	it("skips the initial mount and invalidates when the org scope changes", () => {
		renderWithProviders(<OrgScopeQueryInvalidator />);

		expect(mockInvalidateQueries).not.toHaveBeenCalled();

		act(() => {
			useScopeStore.getState().setScope({
				type: "organization",
				orgId: "org-2",
				orgName: "Globex",
			});
		});

		expect(mockInvalidateQueries).toHaveBeenCalledOnce();
	});
});
