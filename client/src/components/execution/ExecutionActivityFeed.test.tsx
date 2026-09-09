import { describe, expect, it, vi } from "vitest";
import { fireEvent } from "@testing-library/react";
import { renderWithProviders, screen } from "@/test-utils";
import { ExecutionActivityFeed } from "./ExecutionActivityFeed";

describe("ExecutionActivityFeed", () => {
	it("retains messages and pauses following while reading earlier activity", async () => {
		const onViewLogs = vi.fn();
		const logs = [
			{ sequence: 1, message: "Checking accounts" },
			{ sequence: 2, message: "Updating access" },
		];
		const { rerender, user } = renderWithProviders(
			<ExecutionActivityFeed logs={logs} onViewLogs={onViewLogs} />,
		);
		const feed = screen.getByRole("log", { name: "Workflow messages" });
		Object.defineProperties(feed, {
			scrollHeight: { configurable: true, value: 1000 },
			clientHeight: { configurable: true, value: 320 },
		});
		feed.scrollTop = 100;
		fireEvent.scroll(feed);
		rerender(
			<ExecutionActivityFeed
				logs={[
					...logs,
					{ sequence: 3, message: "Sending confirmation" },
				]}
				onViewLogs={onViewLogs}
			/>,
		);
		expect(feed.scrollTop).toBe(100);
		for (const message of [
			"Checking accounts",
			"Updating access",
			"Sending confirmation",
		])
			expect(screen.getByText(message)).toBeInTheDocument();
		await user.click(
			screen.getByRole("button", { name: "Follow latest activity" }),
		);
		expect(feed.scrollTop).toBe(1000);
		await user.click(screen.getByRole("button", { name: "View logs" }));
		expect(onViewLogs).toHaveBeenCalledOnce();
	});
});
