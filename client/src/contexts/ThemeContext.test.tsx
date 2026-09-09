import { afterEach, describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";

import { ThemeToggle } from "@/components/theme-toggle";
import { ThemeProvider, useTheme } from "./ThemeContext";

function ThemeProbe() {
	const { theme, toggleTheme } = useTheme();
	return <button onClick={toggleTheme}>{theme}</button>;
}

afterEach(() => {
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	window.history.replaceState(null, "", "/");
	localStorage.clear();
	document.documentElement.classList.remove("dark");
});

describe("ThemeProvider embedded form override", () => {
	it("defaults embedded forms to light without changing the saved preference", async () => {
		localStorage.setItem("theme", "dark");
		window.history.replaceState(null, "", "/embedded/forms/public/key");
		render(
			<ThemeProvider>
				<ThemeProbe />
			</ThemeProvider>,
		);
		expect(screen.getByText("light")).toBeInTheDocument();
		await waitFor(() =>
			expect(document.documentElement).not.toHaveClass("dark"),
		);
		expect(localStorage.getItem("theme")).toBe("dark");
	});

	it("honors an explicit dark embed theme", async () => {
		localStorage.setItem("theme", "light");
		window.history.replaceState(
			null,
			"",
			"/embedded/forms/public/key?theme=dark",
		);
		render(
			<ThemeProvider>
				<ThemeProbe />
			</ThemeProvider>,
		);
		expect(screen.getByText("dark")).toBeInTheDocument();
		await waitFor(() =>
			expect(document.documentElement).toHaveClass("dark"),
		);
		expect(localStorage.getItem("theme")).toBe("light");
	});
});

describe("ThemeProvider motion preference", () => {
	it("changes and persists the theme without a view transition when motion is reduced", async () => {
		const startTransition = vi.fn();
		vi.stubGlobal(
			"matchMedia",
			vi.fn((query: string) => ({
				matches: query === "(prefers-reduced-motion: reduce)",
				media: query,
				addEventListener: vi.fn(),
				removeEventListener: vi.fn(),
			})),
		);
		const descriptor = Object.getOwnPropertyDescriptor(
			document,
			"startViewTransition",
		);
		Object.defineProperty(document, "startViewTransition", {
			configurable: true,
			value: startTransition,
		});
		try {
			render(
				<ThemeProvider>
					<ThemeProbe />
				</ThemeProvider>,
			);
			await userEvent
				.setup()
				.click(screen.getByRole("button", { name: "dark" }));
			expect(
				screen.getByRole("button", { name: "light" }),
			).toBeInTheDocument();
			expect(document.documentElement).not.toHaveClass("dark");
			expect(localStorage.getItem("theme")).toBe("light");
			expect(startTransition).not.toHaveBeenCalled();
		} finally {
			if (descriptor)
				Object.defineProperty(
					document,
					"startViewTransition",
					descriptor,
				);
			else Reflect.deleteProperty(document, "startViewTransition");
		}
	});
});

describe("ThemeToggle animation ownership", () => {
	it("starts one transition and applies the theme inside its callback", async () => {
		const descriptor = Object.getOwnPropertyDescriptor(
			document,
			"startViewTransition",
		);
		const startTransition = vi.fn((update: () => void) => {
			update();
			expect(document.documentElement).not.toHaveClass("dark");
		});
		Object.defineProperty(document, "startViewTransition", {
			configurable: true,
			value: startTransition,
		});
		try {
			render(
				<ThemeProvider>
					<ThemeToggle />
				</ThemeProvider>,
			);
			await userEvent
				.setup()
				.click(screen.getByRole("button", { name: "Toggle theme" }));
			expect(startTransition).toHaveBeenCalledTimes(1);
			expect(localStorage.getItem("theme")).toBe("light");
		} finally {
			if (descriptor)
				Object.defineProperty(
					document,
					"startViewTransition",
					descriptor,
				);
			else Reflect.deleteProperty(document, "startViewTransition");
		}
	});
});
