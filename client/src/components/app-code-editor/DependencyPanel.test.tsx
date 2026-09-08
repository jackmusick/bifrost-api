/**
 * Focused tests for DependencyPanel.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, screen } from "@testing-library/react";

import { renderWithProviders } from "@/test-utils";

const mockUseAppDependencies = vi.fn();
const mockSearchNpmPackages = vi.fn();

vi.mock("@/hooks/useAppDependencies", () => ({
	useAppDependencies: (...args: unknown[]) => mockUseAppDependencies(...args),
}));

vi.mock("@/lib/npm-search", () => ({
	searchNpmPackages: (...args: unknown[]) => mockSearchNpmPackages(...args),
}));

vi.mock("sonner", () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
	},
}));

import { DependencyPanel } from "./DependencyPanel";

const addDependency = vi.fn();
const removeDependency = vi.fn();

function renderPanel(
	overrides: Partial<Parameters<typeof DependencyPanel>[0]> = {},
) {
	return renderWithProviders(
		<DependencyPanel appId="app-1" {...overrides} />,
	);
}

beforeEach(() => {
	vi.useFakeTimers();
	mockUseAppDependencies.mockReturnValue({
		dependencies: {},
		isLoading: false,
		isSaving: false,
		addDependency,
		removeDependency,
		updateVersion: vi.fn(),
	});
	mockSearchNpmPackages.mockReset();
	addDependency.mockReset();
	removeDependency.mockReset();
});

afterEach(() => {
	vi.runOnlyPendingTimers();
	vi.useRealTimers();
});

describe("DependencyPanel", () => {
	it("lets keyboard users select a search result with arrows and Enter", async () => {
		mockSearchNpmPackages.mockResolvedValue([
			{ name: "left-pad", version: "1.3.0", description: "padding" },
		]);
		renderPanel();

		const input = screen.getByPlaceholderText(/search npm packages/i);
		fireEvent.change(input, { target: { value: "left" } });
		await act(async () => {
			vi.advanceTimersByTime(300);
			await Promise.resolve();
		});

		expect(
			screen.getByRole("option", { name: /left-pad/i }),
		).toBeInTheDocument();

		fireEvent.keyDown(input, { key: "ArrowDown" });
		fireEvent.keyDown(input, { key: "Enter" });

		expect(addDependency).toHaveBeenCalledWith("left-pad", "1.3.0");
	});

	it("shows an empty state when npm search returns no results", async () => {
		mockSearchNpmPackages.mockResolvedValue([]);
		renderPanel();

		const input = screen.getByPlaceholderText(/search npm packages/i);
		fireEvent.change(input, { target: { value: "missing-package" } });
		await act(async () => {
			vi.advanceTimersByTime(300);
			await Promise.resolve();
		});

		expect(screen.getByText(/no packages found/i)).toBeInTheDocument();
		expect(
			screen.getByText(/try a different npm package name/i),
		).toBeInTheDocument();
	});

	it("shows a network error when npm search fails", async () => {
		mockSearchNpmPackages.mockRejectedValue(new Error("offline"));
		renderPanel();

		const input = screen.getByPlaceholderText(/search npm packages/i);
		fireEvent.change(input, { target: { value: "react" } });
		await act(async () => {
			vi.advanceTimersByTime(300);
			await Promise.resolve();
		});

		expect(
			screen.getByText(/could not load npm packages/i),
		).toBeInTheDocument();
		expect(screen.getByText("offline")).toBeInTheDocument();
	});

	it("ignores a stale promise that resolves before the next debounce fires", async () => {
		const resolvers: Array<(value: unknown) => void> = [];
		mockSearchNpmPackages.mockImplementation(
			() =>
				new Promise((resolve) => {
					resolvers.push(resolve);
				}),
		);
		renderPanel();

		const input = screen.getByPlaceholderText(/search npm packages/i);
		fireEvent.change(input, { target: { value: "react" } });
		await act(async () => {
			vi.advanceTimersByTime(300);
			await Promise.resolve();
		});

		fireEvent.change(input, { target: { value: "redux" } });
		await act(async () => {
			await Promise.resolve();
		});

		expect(screen.queryByRole("option", { name: /react/i })).toBeNull();

		await act(async () => {
			resolvers[0]?.([
				{ name: "react", version: "18.0.0", description: "ui" },
			]);
			await Promise.resolve();
		});

		expect(screen.queryByRole("option", { name: /react/i })).toBeNull();

		await act(async () => {
			vi.advanceTimersByTime(300);
			await Promise.resolve();
		});

		await act(async () => {
			resolvers[1]?.([
				{ name: "redux", version: "2.0.0", description: "state" },
			]);
			await Promise.resolve();
		});

		expect(
			screen.getByRole("option", { name: /redux/i }),
		).toBeInTheDocument();
	});

	it("keeps the dropdown closed when Escape is pressed during a pending search", async () => {
		const resolvers: Array<(value: unknown) => void> = [];
		mockSearchNpmPackages.mockImplementation(
			() =>
				new Promise((resolve) => {
					resolvers.push(resolve);
				}),
		);
		renderPanel();

		const input = screen.getByPlaceholderText(/search npm packages/i);
		fireEvent.change(input, { target: { value: "react" } });
		await act(async () => {
			vi.advanceTimersByTime(300);
			await Promise.resolve();
		});

		fireEvent.keyDown(input, { key: "Escape" });

		await act(async () => {
			resolvers[0]?.([
				{ name: "react", version: "18.0.0", description: "ui" },
			]);
			await Promise.resolve();
		});

		expect(screen.queryByRole("listbox")).toBeNull();
		expect(screen.queryByRole("option", { name: /react/i })).toBeNull();
		expect(input).toHaveAttribute("aria-expanded", "false");
	});

	it("clears the old results immediately when the query is emptied", async () => {
		const resolvers: Array<(value: unknown) => void> = [];
		mockSearchNpmPackages.mockImplementation(
			() =>
				new Promise((resolve) => {
					resolvers.push(resolve);
				}),
		);
		renderPanel();

		const input = screen.getByPlaceholderText(/search npm packages/i);
		fireEvent.change(input, { target: { value: "react" } });
		await act(async () => {
			vi.advanceTimersByTime(300);
			await Promise.resolve();
		});

		await act(async () => {
			fireEvent.change(input, { target: { value: "" } });
			await Promise.resolve();
		});

		expect(screen.queryByRole("listbox")).toBeNull();

		await act(async () => {
			resolvers[0]?.([
				{ name: "react", version: "18.0.0", description: "ui" },
			]);
			await Promise.resolve();
		});

		expect(screen.queryByRole("listbox")).toBeNull();
		expect(screen.queryByRole("option", { name: /react/i })).toBeNull();
		expect(input).toHaveValue("");
	});

	it("shows the read-only empty copy without the search hint", () => {
		mockUseAppDependencies.mockReturnValue({
			dependencies: {},
			isLoading: false,
			isSaving: false,
			addDependency,
			removeDependency,
			updateVersion: vi.fn(),
		});
		renderPanel({ readOnly: true });

		expect(
			screen.queryByPlaceholderText(/search npm packages/i),
		).toBeNull();
		expect(screen.getByText(/no packages installed/i)).toBeInTheDocument();
		expect(
			screen.getByText(/dependency changes are unavailable/i),
		).toBeInTheDocument();
		expect(screen.queryByText(/search above/i)).toBeNull();
	});
});

it("shows retry instead of an empty installed list after a failed read", () => {
	const reload = vi.fn();
	mockUseAppDependencies.mockReturnValue({
		dependencies: {},
		isLoading: false,
		isSaving: false,
		loadError: "Could not load installed packages",
		reload,
		addDependency,
		removeDependency,
	});
	renderPanel();
	expect(screen.getByRole("alert")).toHaveTextContent(
		"Could not load installed packages",
	);
	expect(screen.queryByText("No packages installed")).not.toBeInTheDocument();
	fireEvent.click(screen.getByRole("button", { name: "Retry packages" }));
	expect(reload).toHaveBeenCalledOnce();
});
it("keeps a failed add searchable and allows selecting it again", async () => {
	mockSearchNpmPackages.mockResolvedValue([
		{ name: "review-package", version: "1.0.0", description: "Review" },
	]);
	addDependency
		.mockRejectedValueOnce(new Error("offline"))
		.mockResolvedValueOnce(undefined);
	renderPanel();
	const input = screen.getByRole("combobox");
	fireEvent.change(input, { target: { value: "review" } });
	await act(async () => {
		vi.advanceTimersByTime(300);
		await Promise.resolve();
	});
	await act(async () => {
		fireEvent.keyDown(input, { key: "Enter" });
	});
	expect(screen.getByRole("alert")).toHaveTextContent(
		"Could not add review-package",
	);
	expect(input).toHaveValue("review");
	await act(async () => {
		fireEvent.keyDown(input, { key: "Enter" });
	});
	expect(addDependency).toHaveBeenCalledTimes(2);
	expect(input).toHaveValue("");
});
