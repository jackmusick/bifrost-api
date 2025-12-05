/**
 * TabActions - Container for tab-specific actions
 *
 * Use this component to add actions that appear next to tabs.
 * Each tab can provide its own actions via the actions prop.
 */

import { ReactNode } from "react";

interface TabActionsProps {
	children: ReactNode;
}

export function TabActions({ children }: TabActionsProps) {
	return <div className="flex items-center gap-2">{children}</div>;
}
