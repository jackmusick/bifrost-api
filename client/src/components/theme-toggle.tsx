import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/contexts/ThemeContext";

export function ThemeToggle({ className }: { className?: string } = {}) {
	const { theme, setTheme } = useTheme();

	const toggleTheme = (event: React.MouseEvent<HTMLButtonElement>) => {
		const newTheme = theme === "light" ? "dark" : "light";

		// Check if View Transitions API is supported
		if (
			window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
			!document.startViewTransition
		) {
			setTheme(newTheme);
			return;
		}

		// Get the button position for the animation origin
		const button = event.currentTarget;
		const rect = button.getBoundingClientRect();
		const x = rect.left + rect.width / 2;
		const y = rect.top + rect.height / 2;

		// Calculate the radius needed to cover the entire viewport
		const maxRadius = Math.hypot(
			Math.max(x, window.innerWidth - x),
			Math.max(y, window.innerHeight - y),
		);

		document.documentElement.style.setProperty("--transition-x", `${x}px`);
		document.documentElement.style.setProperty("--transition-y", `${y}px`);
		document.documentElement.style.setProperty(
			"--transition-r",
			`${maxRadius}px`,
		);
		setTheme(newTheme);
	};

	return (
		<Button
			variant="ghost"
			size="icon"
			onClick={toggleTheme}
			className={`relative ${className ?? ""}`}
		>
			<Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all motion-reduce:transition-none dark:-rotate-90 dark:scale-0" />
			<Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all motion-reduce:transition-none dark:rotate-0 dark:scale-100" />
			<span className="sr-only">Toggle theme</span>
		</Button>
	);
}
