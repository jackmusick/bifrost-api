import type { HTMLAttributes, ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("framer-motion", () => ({
	AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
	motion: {
		div: (props: HTMLAttributes<HTMLDivElement>) => <div {...props} />,
	},
	useReducedMotion: () => true,
}));

import { NewVersionBanner } from "./NewVersionBanner";

describe("NewVersionBanner", () => {
	it("renders a refresh action when visible", async () => {
		const user = userEvent.setup();
		const onRefresh = vi.fn();

		render(<NewVersionBanner isVisible onRefresh={onRefresh} />);

		expect(screen.getByText(/new version available/i)).toBeInTheDocument();
		await user.click(screen.getByRole("button", { name: /refresh/i }));
		expect(onRefresh).toHaveBeenCalledTimes(1);
	});

	it("renders nothing when hidden", () => {
		const { container } = render(
			<NewVersionBanner isVisible={false} onRefresh={() => {}} />,
		);
		expect(container.firstChild).toBeNull();
	});
});
