import { Home, LogOut, ShieldAlert } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";

export function NoAccess({
	embedded = false,
	message = "Your account does not have access to this system. Please contact your administrator if you believe this is an error.",
}: {
	embedded?: boolean;
	message?: string;
} = {}) {
	const { logout } = useAuth();
	const navigate = useNavigate();

	return (
		<div
			className={
				embedded
					? "flex min-w-0 justify-center py-6 sm:py-12"
					: "flex min-h-[100dvh] items-center justify-center bg-background p-4"
			}
		>
			<Card
				className={`w-full max-w-md ${embedded ? "" : "max-h-[calc(100dvh-2rem)] overflow-y-auto"}`}
			>
				<CardContent className="flex flex-col items-center justify-center px-4 py-6 text-center sm:px-6 sm:py-8">
					<ShieldAlert className="h-16 w-16 text-destructive" />
					<h1 className="mt-6 text-pretty text-2xl font-bold tracking-tight [overflow-wrap:anywhere]">
						Access Denied
					</h1>
					<p className="mt-4 text-balance text-muted-foreground [overflow-wrap:anywhere]">
						{message}
					</p>
					<div className="mt-6 flex w-full flex-col gap-2">
						<Button
							onClick={() => navigate("/")}
							className="h-11 w-full"
						>
							<Home className="h-4 w-4" />
							Return to Dashboard
						</Button>
						<Button
							onClick={logout}
							variant="ghost"
							className="h-11 w-full"
						>
							<LogOut className="h-4 w-4" />
							Sign Out
						</Button>
					</div>
				</CardContent>
			</Card>
		</div>
	);
}
