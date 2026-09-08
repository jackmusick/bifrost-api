import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, renderWithProviders, screen, waitFor } from "@/test-utils";
import * as clipboard from "@/lib/clipboard";
import { CronTester } from "./CronTester";

const mocks = vi.hoisted(() => ({
	authFetch: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({
	authFetch: (...args: unknown[]) => mocks.authFetch(...args),
}));

vi.mock("@/lib/clipboard", () => ({
	copyToClipboard: vi.fn(),
}));

function makeResponse(data: unknown) {
	return {
		ok: true,
		status: 200,
		statusText: "OK",
		text: async () => JSON.stringify(data),
		json: async () => data,
	} as const;
}

function makeErrorResponse(
	bodyText: string,
	status = 422,
	statusText = "Unprocessable Content",
) {
	return {
		ok: false,
		status,
		statusText,
		text: async () => bodyText,
		json: async () => ({ message: bodyText }),
	} as const;
}

function deferred<T>() {
	let resolve!: (value: T) => void;
	let reject!: (reason?: unknown) => void;
	const promise = new Promise<T>((res, rej) => {
		resolve = res;
		reject = rej;
	});
	return { promise, resolve, reject };
}

beforeEach(() => {
	mocks.authFetch.mockReset();
});

describe("CronTester", () => {
	it("validates expressions and shows upcoming runs", async () => {
		mocks.authFetch.mockResolvedValue(
			makeResponse({
				valid: true,
				human_readable: "Runs daily at 9:00 AM",
				next_runs: [
					"2026-09-08T13:00:00.000Z",
					"2026-09-09T13:00:00.000Z",
				],
			}),
		);

		renderWithProviders(<CronTester />);

		fireEvent.change(screen.getByPlaceholderText("0 9 * * *"), {
			target: { value: "0 9 * * *" },
		});

		await waitFor(() => expect(mocks.authFetch).toHaveBeenCalledTimes(1));
		expect(screen.getByText("Runs daily at 9:00 AM")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Copy expression" })).toHaveClass(
			"min-h-11",
		);
		expect(screen.getByText("Next runs")).toBeInTheDocument();
	});

	it("shows a retry path for invalid validation results", async () => {
		mocks.authFetch.mockResolvedValue(
			makeResponse({
				valid: false,
				human_readable: "Invalid cron expression",
				error: "The expression is malformed",
			}),
		);

		renderWithProviders(<CronTester />);

		fireEvent.change(screen.getByPlaceholderText("0 9 * * *"), {
			target: { value: "bad cron" },
		});

		await waitFor(() =>
			expect(screen.getByText("The expression is malformed")).toBeInTheDocument(),
		);
		expect(screen.getByRole("button", { name: "Retry" })).toHaveClass(
			"min-h-11",
		);

		fireEvent.click(screen.getByRole("button", { name: "Retry" }));
		await waitFor(() => expect(mocks.authFetch).toHaveBeenCalledTimes(2));
	});

	it("ignores stale validation results when a newer expression is entered", async () => {
		const first = deferred<ReturnType<typeof makeResponse>>();
		const second = deferred<ReturnType<typeof makeResponse>>();

		mocks.authFetch
			.mockImplementationOnce(() => first.promise)
			.mockImplementationOnce(() => second.promise);

		renderWithProviders(<CronTester />);

		fireEvent.change(screen.getByPlaceholderText("0 9 * * *"), {
			target: { value: "0 9 * * *" },
		});
		await waitFor(() => expect(mocks.authFetch).toHaveBeenCalledTimes(1));

		fireEvent.change(screen.getByPlaceholderText("0 9 * * *"), {
			target: { value: "0 10 * * *" },
		});
		await waitFor(() => expect(mocks.authFetch).toHaveBeenCalledTimes(2));

		first.resolve(
			makeResponse({
				valid: true,
				human_readable: "Old result",
				next_runs: ["2026-09-08T13:00:00.000Z"],
			}),
		);
		await waitFor(() =>
			expect(screen.queryByText("Old result")).not.toBeInTheDocument(),
		);

		second.resolve(
			makeResponse({
				valid: true,
				human_readable: "New result",
				next_runs: ["2026-09-09T13:00:00.000Z"],
			}),
		);
		await waitFor(() =>
			expect(screen.getByText("New result")).toBeInTheDocument(),
		);
	});

	it("shows explicit HTTP validation error details", async () => {
		mocks.authFetch.mockResolvedValue(
			makeErrorResponse("Cron must contain 5 fields"),
		);

		renderWithProviders(<CronTester />);

		fireEvent.change(screen.getByPlaceholderText("0 9 * * *"), {
			target: { value: "bad cron" },
		});

		expect(
			await screen.findByText(
				/Unprocessable Content: Cron must contain 5 fields/i,
			),
		).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Retry" })).toHaveClass(
			"min-h-11",
		);
	});

	it("shows a copy failure message and retries successfully", async () => {
		const copyToClipboard = vi
			.spyOn(clipboard, "copyToClipboard")
			.mockResolvedValueOnce(false)
			.mockResolvedValueOnce(true);

		mocks.authFetch.mockResolvedValue(
			makeResponse({
				valid: true,
				human_readable: "Runs daily at 9:00 AM",
			}),
		);

		const { user } = renderWithProviders(<CronTester />);

		fireEvent.change(screen.getByPlaceholderText("0 9 * * *"), {
			target: { value: "0 9 * * *" },
		});
		await waitFor(() => expect(mocks.authFetch).toHaveBeenCalledTimes(1));

		await user.click(screen.getByRole("button", { name: "Copy expression" }));
		expect(
			await screen.findByText(/could not copy the cron expression/i),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Retry expression copy" }),
		).toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: "Retry expression copy" }));
		await waitFor(() => expect(copyToClipboard).toHaveBeenCalledTimes(2));
		expect(screen.getByRole("button", { name: "Copied expression" })).toBeInTheDocument();
		expect(
			screen.queryByText(/could not copy the cron expression/i),
		).not.toBeInTheDocument();
		copyToClipboard.mockRestore();
	});
});
