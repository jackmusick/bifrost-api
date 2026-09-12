/**
 * Header affordance for setting up a passkey without occupying page content.
 */

import { useNavigate } from "react-router-dom";
import { Fingerprint } from "lucide-react";

import { Button } from "@/components/ui/button";
import { usePasskeyList } from "@/hooks/usePasskeys";
import { supportsPasskeys } from "@/services/passkeys";

const DISMISSED_KEY = "passkey_banner_dismissed";

function isDismissed(): boolean {
	try {
		return localStorage.getItem(DISMISSED_KEY) === "true";
	} catch {
		return false;
	}
}

export function PasskeySetupBadge() {
	const navigate = useNavigate();
	const isSupported = supportsPasskeys();
	const { data: passkeyData, isLoading } = usePasskeyList();

	if (
		isLoading ||
		!isSupported ||
		isDismissed() ||
		(passkeyData && passkeyData.count > 0)
	) {
		return null;
	}

	return (
		<Button
			variant="ghost"
			size="icon-lg"
			className="relative mr-1 sm:mr-2"
			onClick={() => navigate("/user-settings/security")}
			title="Set up passkey"
			aria-label="Set up passkey"
		>
			<Fingerprint className="h-5 w-5" />
			<span
				aria-hidden="true"
				data-slot="passkey-setup-indicator"
				className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-primary ring-2 ring-background"
			/>
		</Button>
	);
}
