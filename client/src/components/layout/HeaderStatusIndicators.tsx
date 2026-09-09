import { VersionUpdateBanner } from "./VersionUpdateBanner";
import { FileActivityIndicator } from "./FileActivityIndicator";

export function HeaderStatusIndicators({
	isPlatformAdmin,
}: {
	isPlatformAdmin: boolean;
}) {
	return (
		<>
			<VersionUpdateBanner />
			{isPlatformAdmin && <FileActivityIndicator />}
		</>
	);
}
