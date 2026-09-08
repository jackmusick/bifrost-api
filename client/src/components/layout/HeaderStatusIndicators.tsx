import { VersionUpdateBanner } from "./VersionUpdateBanner";
import { FileActivityIndicator } from "./FileActivityIndicator";
import { PasskeySetupBadge } from "@/components/PasskeySetupBadge";

export function HeaderStatusIndicators({
	isPlatformAdmin,
}: {
	isPlatformAdmin: boolean;
}) {
	return (
		<>
			<VersionUpdateBanner />
			{isPlatformAdmin && <FileActivityIndicator />}
			<PasskeySetupBadge />
		</>
	);
}
