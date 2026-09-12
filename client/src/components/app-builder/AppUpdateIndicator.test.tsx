import type { HTMLAttributes, ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("framer-motion", () => ({
	AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
	motion: {
		div: (props: HTMLAttributes<HTMLDivElement>) => <div {...props} />,
	},
	useReducedMotion: () => true,
}));

import { AppUpdateIndicator } from "./AppUpdateIndicator";

describe("AppUpdateIndicator", () => {
	it("renders the updater name and timestamp metadata", () => {
		const timestamp = new Date("2026-09-07T12:00:00.000Z");

		const { container } = render(
			<AppUpdateIndicator
				lastUpdate={{ userName: "Ada Lovelace", timestamp }}
			/>,
		);

		expect(container.firstChild).toHaveTextContent("Ada Lovelace");
		expect(container.querySelector("time")).toHaveAttribute(
			"dateTime",
			timestamp.toISOString(),
		);
		expect(screen.getByText(/updated/i)).toBeInTheDocument();
	});

	it("renders nothing when there is no update", () => {
		const { container } = render(<AppUpdateIndicator lastUpdate={null} />);
		expect(container.firstChild).toBeNull();
	});
});
