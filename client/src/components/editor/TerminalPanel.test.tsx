/**
 * Component tests for the editor terminal panel.
 */

// @vitest-environment happy-dom

import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, renderWithProviders, screen, waitFor } from "@/test-utils";
import { useEditorStore } from "@/stores/editorStore";
import { useExecutionStreamStore } from "@/stores/executionStreamStore";
import { TerminalPanel } from "./TerminalPanel";

const scrollToMock = vi.fn();
const reducedMotionMatches = false;

vi.mock("@/hooks/useMediaQuery", () => ({
	useMediaQuery: (query: string) =>
		query === "(prefers-reduced-motion: reduce)"
			? reducedMotionMatches
			: false,
}));

vi.mock("@/components/editor/TerminalLogMessage", () => ({
	TerminalLogMessage: ({ message }: { message: string }) => <span>{message}</span>,
}));

vi.mock("@/components/editor/TerminalExecutionResult", () => ({
	TerminalExecutionResult: () => <div data-testid="terminal-result" />,
}));

function makeStreamingLog(message: string, timestamp: string) {
	return {
		level: "INFO",
		message,
		timestamp,
	};
}

function defineViewportMetrics(
	element: HTMLElement,
	{ scrollHeight, clientHeight, scrollTop }: {
		scrollHeight: number;
		clientHeight: number;
		scrollTop: number;
	},
) {
	Object.defineProperty(element, "scrollHeight", {
		configurable: true,
		value: scrollHeight,
	});
	Object.defineProperty(element, "clientHeight", {
		configurable: true,
		value: clientHeight,
	});
	Object.defineProperty(element, "scrollTop", {
		configurable: true,
		writable: true,
		value: scrollTop,
	});
}

beforeEach(() => {
	scrollToMock.mockClear();
	Object.defineProperty(HTMLElement.prototype, "scrollTo", {
		configurable: true,
		value: scrollToMock,
	});

	useEditorStore.setState({
		terminalOutput: null,
		currentStreamingExecutionId: null,
	});

	useExecutionStreamStore.setState({
		streams: {},
	});
});

describe("TerminalPanel", () => {
	it("pauses follow mode when the user scrolls up, then resumes at the bottom", async () => {
		useEditorStore.setState({
			currentStreamingExecutionId: "exec-1",
		});
		useExecutionStreamStore.getState().startStreaming("exec-1");
		useExecutionStreamStore.getState().appendLogs("exec-1", [
			makeStreamingLog("step 1", "2026-09-05T12:00:00Z"),
			makeStreamingLog("step 2", "2026-09-05T12:00:01Z"),
			makeStreamingLog("step 3", "2026-09-05T12:00:02Z"),
		]);

		const { user } = renderWithProviders(<TerminalPanel />);
		const viewport = screen.getByTestId("terminal-log-viewport");
		defineViewportMetrics(viewport, {
			scrollHeight: 1200,
			clientHeight: 300,
			scrollTop: 900,
		});

		await waitFor(() => {
			expect(scrollToMock).toHaveBeenCalled();
		});

		defineViewportMetrics(viewport, {
			scrollHeight: 1200,
			clientHeight: 300,
			scrollTop: 100,
		});
		fireEvent.scroll(viewport);

		expect(
			screen.getByRole("button", { name: /jump to latest terminal output/i }),
		).toBeInTheDocument();

		const callsAfterPause = scrollToMock.mock.calls.length;
		useExecutionStreamStore.getState().appendLog(
			"exec-1",
			makeStreamingLog("step 4", "2026-09-05T12:00:03Z"),
		);
		await waitFor(() => {
			expect(scrollToMock.mock.calls.length).toBe(callsAfterPause);
		});

		defineViewportMetrics(viewport, {
			scrollHeight: 1400,
			clientHeight: 300,
			scrollTop: 1100,
		});
		fireEvent.scroll(viewport);
		await waitFor(() => {
			expect(
				screen.queryByRole("button", {
					name: /jump to latest terminal output/i,
				}),
			).toBeNull();
		});

		useExecutionStreamStore.getState().appendLog(
			"exec-1",
			makeStreamingLog("step 5", "2026-09-05T12:00:04Z"),
		);
		await waitFor(() => {
			expect(scrollToMock.mock.calls.length).toBeGreaterThan(
				callsAfterPause,
			);
		});

		expect(
			screen.getByRole("button", { name: /clear terminal output/i }),
		).toBeInTheDocument();
		await user.click(
			screen.getByRole("button", { name: /clear terminal output/i }),
		);
		expect(useEditorStore.getState().terminalOutput).toBeNull();
	});

	it("keeps jump to latest available after completion when the user has scrolled up", async () => {
		useEditorStore.setState({
			currentStreamingExecutionId: "exec-2",
		});
		useExecutionStreamStore.getState().startStreaming("exec-2");
		useExecutionStreamStore.getState().appendLog(
			"exec-2",
			makeStreamingLog("processing", "2026-09-05T12:10:00Z"),
		);

		const { user } = renderWithProviders(<TerminalPanel />);
		const viewport = screen.getByTestId("terminal-log-viewport");
		defineViewportMetrics(viewport, {
			scrollHeight: 1000,
			clientHeight: 300,
			scrollTop: 200,
		});
		fireEvent.scroll(viewport);

		expect(
			screen.getByRole("button", { name: /jump to latest terminal output/i }),
		).toBeInTheDocument();
		const callsBeforeCompletion = scrollToMock.mock.calls.length;

		await act(async () => {
			useEditorStore.setState({
				currentStreamingExecutionId: null,
				terminalOutput: {
					executions: [
						{
							timestamp: "2026-09-05T12:10:05Z",
							loggerOutput: [
								{
									level: "SUCCESS",
									message: "Done",
									source: "system",
									timestamp: "2026-09-05T12:10:05Z",
								},
							],
							variables: {},
							status: "Success",
							error: undefined,
						},
					],
				},
			});
			useExecutionStreamStore.setState({ streams: {} });
		});
		await waitFor(() => {
			expect(scrollToMock.mock.calls.length).toBe(callsBeforeCompletion);
		});
		expect(viewport.scrollTop).toBe(200);
		expect(
			screen.getByRole("button", { name: /jump to latest terminal output/i }),
		).toBeInTheDocument();
		expect(screen.queryByTestId("terminal-loading-bar")).toBeNull();
		expect(screen.getByText("Done")).toBeInTheDocument();

		await user.click(
			screen.getByRole("button", { name: /jump to latest terminal output/i }),
		);
		expect(scrollToMock.mock.calls.length).toBeGreaterThan(
			callsBeforeCompletion,
		);
	});
});
