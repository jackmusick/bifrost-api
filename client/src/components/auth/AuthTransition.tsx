import { motion, useReducedMotion } from "framer-motion";

import { Logo } from "@/components/branding/Logo";
import { Card, CardContent } from "@/components/ui/card";
import { useApplicationName } from "@/lib/applicationName";

/**
 * Full-card "we're finishing up" state for auth flows.
 *
 * Shown in the window between a credential/passkey/password success and the
 * redirect, where the server is still resolving the session. Without it the
 * page sits on the form (with only a small button spinner) for a beat on a
 * slow connection, which reads as "nothing happened".
 */
export function AuthTransition({ message }: { message: string }) {
	const applicationName = useApplicationName();
	const reducedMotion = useReducedMotion();
	return (
		<div className="min-h-svh flex items-center justify-center bg-background px-4 py-8">
			<Card className="w-full max-w-md rounded-[var(--bf-radius-feature)] border-border shadow-none">
				<CardContent className="flex flex-col items-center gap-4 py-12 text-center">
					<motion.div
						initial={reducedMotion ? false : { opacity: 0 }}
						animate={{ opacity: 1 }}
						transition={{ duration: reducedMotion ? 0 : 0.22 }}
						className="flex justify-center"
					>
						<Logo
							type="square"
							className="h-16 w-16"
							alt={applicationName}
						/>
					</motion.div>
					<div
						aria-hidden="true"
						className="route-transition-progress-track h-1 w-40 overflow-hidden rounded-full"
					>
						<div
							className="route-transition-progress-fill h-full w-full"
							data-state="loading"
						/>
					</div>
					<p role="status" className="text-sm text-muted-foreground">
						{message}
					</p>
				</CardContent>
			</Card>
		</div>
	);
}
