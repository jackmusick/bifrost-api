/**
 * Component tests for RunStatusBadge — the History feed's quiet-success /
 * loud-failure status badge. The visual hierarchy IS the contract here:
 * success must render as a quiet outline (no loud green fill), failures
 * must use the destructive variant, and Scheduled exposes its fire time
 * via a title tooltip.
 */

import { describe, it, expect } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { RunStatusBadge } from "./RunStatusBadge";

describe("RunStatusBadge — labels", () => {
	it.each([
		["Success", /^completed$/i],
		["Failed", /^failed$/i],
		["Timeout", /timed out/i],
		["CompletedWithErrors", /completed with errors/i],
		["Running", /running/i],
		["Pending", /pending/i],
		["Scheduled", /scheduled/i],
		["Cancelling", /cancelling/i],
		["Cancelled", /cancelled/i],
	])("renders %s with a readable label", (status, expectedLabel) => {
		renderWithProviders(<RunStatusBadge status={status} />);
		expect(screen.getByText(expectedLabel)).toBeInTheDocument();
	});

	it("falls back to the raw status string for unknown statuses", () => {
		renderWithProviders(<RunStatusBadge status="SomethingNew" />);
		expect(screen.getByText("SomethingNew")).toBeInTheDocument();
	});
});

describe("RunStatusBadge — visual hierarchy", () => {
	it("renders Success quietly: no solid green fill, muted text", () => {
		renderWithProviders(<RunStatusBadge status="Success" />);
		const badge = screen
			.getByText(/^completed$/i)
			.closest('[data-slot="badge"]');
		expect(badge).toBeTruthy();
		if (!badge) return;
		expect(badge.className).toContain("text-[color:var(--bf-success)]");
		expect(badge.className).not.toMatch(/bg-green/);
	});

	it("renders Failed with semantic danger styling", () => {
		renderWithProviders(<RunStatusBadge status="Failed" />);
		const badge = screen.getByText(/^failed$/i).closest('[data-slot="badge"]');
		expect(badge).toBeTruthy();
		if (!badge) return;
		expect(badge.getAttribute("style")).toContain("color: var(--bf-danger)");
	});

	it("renders Timeout with semantic danger styling", () => {
		renderWithProviders(<RunStatusBadge status="Timeout" />);
		const badge = screen.getByText(/timed out/i).closest('[data-slot="badge"]');
		expect(badge).toBeTruthy();
		if (!badge) return;
		expect(badge.getAttribute("style")).toContain("color: var(--bf-danger)");
	});
});

describe("RunStatusBadge — active indicator", () => {
	it.each(["Running", "Pending", "Cancelling"] as const)(
		"shows the live gradient indicator for %s",
		(status) => {
			renderWithProviders(<RunStatusBadge status={status} />);
			expect(
				screen.getByTestId("run-status-activity-indicator"),
			).toBeInTheDocument();
		},
	);
});

describe("RunStatusBadge — scheduled tooltip", () => {
	it("exposes the scheduled fire time via a title attribute", () => {
		renderWithProviders(
			<RunStatusBadge
				status="Scheduled"
				scheduledAt="2030-01-01T09:00:00Z"
			/>,
		);
		const badge = screen.getByText(/scheduled/i);
		expect(badge).toHaveAttribute(
			"title",
			expect.stringContaining("Scheduled for"),
		);
	});

	it("omits the title when no scheduledAt is provided", () => {
		renderWithProviders(<RunStatusBadge status="Scheduled" />);
		const badge = screen.getByText(/scheduled/i);
		expect(badge).not.toHaveAttribute("title");
	});
});

describe("RunStatusBadge — pending wait variants", () => {
	it("shows queue position when waiting in queue", () => {
		renderWithProviders(
			<RunStatusBadge
				status="Pending"
				waitReason="queued"
				queuePosition={3}
			/>,
		);
		expect(screen.getByText(/queued — position 3/i)).toBeInTheDocument();
	});

	it("shows memory figures under memory pressure", () => {
		renderWithProviders(
			<RunStatusBadge
				status="Pending"
				waitReason="memory_pressure"
				availableMemoryMb={512}
				requiredMemoryMb={1024}
			/>,
		);
		expect(
			screen.getByText(/heavy load \(512MB \/ 1024MB\)/i),
		).toBeInTheDocument();
	});

	it("falls back to plain Pending without wait metadata", () => {
		renderWithProviders(<RunStatusBadge status="Pending" />);
		expect(screen.getByText(/^pending$/i)).toBeInTheDocument();
	});
});
