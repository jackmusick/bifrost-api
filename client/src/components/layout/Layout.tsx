import { useFileActivity } from "@/hooks/useFileActivity";
import { PageShell } from "./PageShell";

export function Layout() {
	useFileActivity();
	return <PageShell padded />;
}
