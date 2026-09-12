import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Calendar as CalendarIcon } from "lucide-react";

import { APP_CODE_COMPONENTS, Button, CalendarPicker } from "./components";
import {
	CommandDialog,
	CommandInput,
	CommandItem,
	CommandList,
} from "@/components/ui/command";

describe("V1 design-system compatibility", () => {
	it("keeps Button ref forwarding and native button props intact", async () => {
		const user = userEvent.setup();
		const ref = React.createRef<HTMLButtonElement>();
		const onClick = vi.fn();

		render(
			<Button ref={ref} type="submit" aria-label="Save changes" onClick={onClick}>
				Save
			</Button>,
		);

		const button = screen.getByRole("button", { name: "Save changes" });
		expect(ref.current).toBe(button);
		expect(button).toHaveAttribute("type", "submit");
		expect(button).toHaveAttribute("data-slot", "button");

		await user.click(button);
		expect(onClick).toHaveBeenCalledTimes(1);
	});

	it("keeps Button asChild ref forwarding and slot props intact", () => {
		let attached: HTMLElement | null = null;

		render(
			<Button asChild ref={(node) => { attached = node; }}>
				<a href="/docs">Docs</a>
			</Button>,
		);

		const link = screen.getByRole("link", { name: "Docs" });
		expect(attached).toBe(link);
		expect(link).toHaveAttribute("href", "/docs");
		expect(link).toHaveAttribute("data-slot", "button");
		expect(link).toHaveAttribute("data-variant", "default");
	});

	it("keeps CommandDialog auto-wrapping bare command children", () => {
		render(
			<CommandDialog open title="Palette" description="Search">
				<CommandInput placeholder="Search commands" />
				<CommandList>
					<CommandItem value="one">One</CommandItem>
				</CommandList>
			</CommandDialog>,
		);

		expect(screen.getByPlaceholderText("Search commands")).toBeInTheDocument();
		expect(screen.getByRole("option", { name: "One" })).toBeInTheDocument();
		expect(document.querySelectorAll('[data-slot="command"]')).toHaveLength(1);
	});

	it("keeps CalendarPicker distinct from the Lucide Calendar icon", () => {
		expect(APP_CODE_COMPONENTS.CalendarPicker).toBe(CalendarPicker);
		expect(APP_CODE_COMPONENTS.CalendarPicker).not.toBe(CalendarIcon);
		expect(typeof CalendarPicker).toBe("function");
	});
});
