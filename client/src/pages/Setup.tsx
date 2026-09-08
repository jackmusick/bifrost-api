/**
 * Setup Wizard Page
 *
 * First-time setup for creating the initial admin user.
 * Only shown when no users exist in the system.
 *
 * Supports two registration methods:
 * 1. Passkey (preferred) - Passwordless via Face ID, Touch ID, etc.
 * 2. Password (fallback) - Traditional password + MFA setup
 */

import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { registerUser } from "@/services/auth";
import { setupWithPasskey } from "@/services/passkeys";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
} from "@/components/ui/card";
import { Loader2, Mail, User } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { Logo } from "@/components/branding/Logo";
import { useApplicationName } from "@/lib/applicationName";
import { toast } from "sonner";
import { AuthSetupSteps } from "@/components/auth/AuthSetupSteps";

type SetupMode = "choose" | "auth";

export function Setup() {
	const reducedMotion = useReducedMotion();
	const headingRef = useRef<HTMLHeadingElement>(null);
	const navigate = useNavigate();
	const applicationName = useApplicationName();
	const {
		needsSetup,
		isLoading: authLoading,
		checkAuthStatus,
		completeLoginWithToken,
	} = useAuth();

	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [mode, setMode] = useState<SetupMode>("choose");

	const [email, setEmail] = useState("");
	const [name, setName] = useState("");

	useEffect(() => {
		if (mode === "auth") headingRef.current?.focus();
	}, [mode]);

	// Redirect if setup not needed
	useEffect(() => {
		if (!authLoading && !needsSetup) {
			navigate("/login");
		}
	}, [authLoading, needsSetup, navigate]);

	const handlePasskeySetup = async () => {
		setError(null);
		setIsLoading(true);
		try {
			const result = await setupWithPasskey(email, name);
			completeLoginWithToken(result.access_token);
			await checkAuthStatus();
			toast.success("Account created successfully!");
			navigate("/");
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Passkey setup failed",
			);
			setIsLoading(false);
		}
	};

	const handlePasswordSetup = async (password: string) => {
		setError(null);
		setIsLoading(true);
		try {
			await registerUser(email, password, name);
			await checkAuthStatus();
			navigate("/login", {
				state: { message: "Account created! Please sign in." },
			});
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Account creation failed",
			);
			setIsLoading(false);
		}
	};

	if (authLoading) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-background">
				<Loader2 className="h-8 w-8 animate-spin motion-reduce:animate-none text-muted-foreground" />
			</div>
		);
	}

	const renderChooseMode = () => (
		<form
			className="space-y-4"
			onSubmit={(event) => {
				event.preventDefault();
				setError(null);
				setMode("auth");
			}}
		>
			<div className="space-y-2">
				<Label htmlFor="name">Name</Label>
				<div className="relative">
					<User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
					<Input
						id="name"
						autoComplete="name"
						type="text"
						placeholder="Your name"
						value={name}
						onChange={(e) => setName(e.target.value)}
						className="h-11 pl-10"
						autoFocus
					/>
				</div>
			</div>
			<div className="space-y-2">
				<Label htmlFor="email">Email</Label>
				<div className="relative">
					<Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
					<Input
						id="email"
						autoComplete="email"
						type="email"
						placeholder="admin@example.com"
						value={email}
						onChange={(e) => setEmail(e.target.value)}
						className="h-11 pl-10"
						required
					/>
				</div>
			</div>
			<Button
				type="submit"
				className="min-h-11 w-full mt-2"
				disabled={!email}
			>
				Continue
			</Button>
		</form>
	);

	return (
		<div className="min-h-svh flex items-center justify-center bg-background px-4 py-8">
			<motion.div
				initial={reducedMotion ? false : { opacity: 0, y: 4 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{
					duration: reducedMotion ? 0 : 0.36,
					ease: "easeOut",
				}}
				className="w-full max-w-md"
			>
				<Card className="rounded-[var(--bf-radius-feature)] border-border shadow-none">
					<CardHeader className="text-center space-y-4 pb-2">
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
						<div className="space-y-1">
							<h1
								ref={headingRef}
								tabIndex={-1}
								className="font-display text-2xl font-semibold tracking-tight outline-none"
							>
								Welcome to {applicationName}
							</h1>
							<CardDescription className="text-base">
								{mode === "choose" &&
									"Create your admin account to get started"}
								{mode === "auth" &&
									"Choose how to secure your account"}
							</CardDescription>
							{mode === "auth" && (
								<p className="pt-2 text-sm font-medium [overflow-wrap:anywhere]">
									{email}
								</p>
							)}
						</div>
					</CardHeader>
					<CardContent>
						{mode === "choose" && renderChooseMode()}
						{mode === "auth" && (
							<>
								<AuthSetupSteps
									email={email}
									onPasskeyRegister={handlePasskeySetup}
									onPasswordRegister={handlePasswordSetup}
									isPending={isLoading}
									error={error}
								/>
								<Button
									type="button"
									variant="ghost"
									className="mt-3 min-h-11 w-full"
									disabled={isLoading}
									onClick={() => {
										setMode("choose");
										setError(null);
									}}
								>
									Change account details
								</Button>
							</>
						)}
					</CardContent>
				</Card>
			</motion.div>
		</div>
	);
}

export default Setup;
