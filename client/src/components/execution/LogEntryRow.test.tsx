import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { LogEntryRow } from "./LogEntryRow";

it.each([
	["WARN", "warning", "--bf-warning"],
	["critical", "error", "--bf-danger"],
	["TRACEBACK", "error", "--bf-danger"],
	["DEBUG", "debug", "--muted-foreground"],
	["INFO", "info", "--bf-info"],
])("preserves %s severity across log surfaces", (level, severity, token) => {
	render(
		<LogEntryRow as="li" level={level}>
			Message
		</LogEntryRow>,
	);
	const row = screen.getByText("Message");
	expect(row).toHaveAttribute("data-severity", severity);
	expect(row.getAttribute("style")).toContain(token);
});
