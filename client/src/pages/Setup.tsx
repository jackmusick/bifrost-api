/**
 * Setup Wizard Page
 *
 * First-time setup for creating the initial admin user.
 * Only shown when no users exist in the system.
 * After registration, redirects to login for the standard auth flow.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { registerUser } from "@/services/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Mail, Lock, User } from "lucide-react";
import { motion } from "framer-motion";
import { Logo } from "@/components/branding/Logo";

export function Setup() {
	const navigate = useNavigate();
	const { needsSetup, isLoading: authLoading, checkAuthStatus } = useAuth();

	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	// Account form
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [confirmPassword, setConfirmPassword] = useState("");
	const [name, setName] = useState("");

	// Redirect if setup not needed
	useEffect(() => {
		if (!authLoading && !needsSetup) {
			navigate("/login");
		}
	}, [authLoading, needsSetup, navigate]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);

		if (password !== confirmPassword) {
			setError("Passwords do not match");
			return;
		}

		if (password.length < 8) {
			setError("Password must be at least 8 characters");
			return;
		}

		setIsLoading(true);

		try {
			// Register the user
			await registerUser(email, password, name);

			// Refresh auth status so needsSetup becomes false
			await checkAuthStatus();

			// Redirect to login - the standard login flow handles MFA setup
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
				<Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
			</div>
		);
	}

	return (
		<div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-primary/5 p-4">
			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.4, ease: "easeOut" }}
				className="w-full max-w-md"
			>
				<Card className="border-primary/10 shadow-xl shadow-primary/5">
					<CardHeader className="text-center space-y-4 pb-2">
						<motion.div
							initial={{ scale: 0.8, opacity: 0 }}
							animate={{ scale: 1, opacity: 1 }}
							transition={{ delay: 0.1, duration: 0.3 }}
							className="flex justify-center"
						>
							<Logo
								type="square"
								className="h-16 w-16"
								alt="Bifrost"
							/>
						</motion.div>
						<div className="space-y-1">
							<CardTitle className="text-2xl font-bold tracking-tight">
								Welcome to Bifrost
							</CardTitle>
							<CardDescription className="text-base">
								Create your admin account to get started
							</CardDescription>
						</div>
					</CardHeader>
					<CardContent>
						{error && (
							<Alert variant="destructive" className="mb-4">
								<AlertDescription>{error}</AlertDescription>
							</Alert>
						)}

						<form onSubmit={handleSubmit} className="space-y-4">
							<div className="space-y-2">
								<Label htmlFor="name">Name</Label>
								<div className="relative">
									<User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
									<Input
										id="name"
										type="text"
										placeholder="Your name"
										value={name}
										onChange={(e) =>
											setName(e.target.value)
										}
										className="pl-10"
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
										type="email"
										placeholder="admin@example.com"
										value={email}
										onChange={(e) =>
											setEmail(e.target.value)
										}
										className="pl-10"
										required
									/>
								</div>
							</div>
							<div className="space-y-2">
								<Label htmlFor="password">Password</Label>
								<div className="relative">
									<Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
									<Input
										id="password"
										type="password"
										placeholder="At least 8 characters"
										value={password}
										onChange={(e) =>
											setPassword(e.target.value)
										}
										className="pl-10"
										required
										minLength={8}
									/>
								</div>
							</div>
							<div className="space-y-2">
								<Label htmlFor="confirmPassword">
									Confirm Password
								</Label>
								<div className="relative">
									<Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
									<Input
										id="confirmPassword"
										type="password"
										placeholder="Confirm your password"
										value={confirmPassword}
										onChange={(e) =>
											setConfirmPassword(e.target.value)
										}
										className="pl-10"
										required
									/>
								</div>
							</div>
							<Button
								type="submit"
								className="w-full"
								disabled={
									isLoading ||
									!email ||
									!password ||
									!confirmPassword
								}
							>
								{isLoading ? (
									<Loader2 className="h-4 w-4 animate-spin mr-2" />
								) : null}
								Create Account
							</Button>
						</form>
					</CardContent>
				</Card>
			</motion.div>
		</div>
	);
}

export default Setup;
