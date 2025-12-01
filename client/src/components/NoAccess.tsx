import { ShieldAlert } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { logout } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";

export function NoAccess() {
	return (
		<div className="min-h-screen bg-background flex items-center justify-center p-4">
			<Card className="max-w-md w-full">
				<CardContent className="flex flex-col items-center justify-center py-12 text-center">
					<ShieldAlert className="h-16 w-16 text-destructive" />
					<h1 className="mt-6 text-2xl font-bold tracking-tight">
						Access Denied
					</h1>
					<p className="mt-4 text-muted-foreground">
						Your account does not have access to this system. Please
						contact your administrator if you believe this is an
						error.
					</p>
					<Button onClick={logout} variant="outline" className="mt-6">
						Sign Out
					</Button>
				</CardContent>
			</Card>
		</div>
	);
}
