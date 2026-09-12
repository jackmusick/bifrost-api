export function routeRevealKey(
	pathname: string,
	navigationState?: unknown,
): string {
	if (
		/^\/chat\/[^/]+$/.test(pathname) &&
		pathname !== "/chat/artifacts" &&
		typeof navigationState === "object" &&
		navigationState !== null &&
		"preserveChatDraft" in navigationState &&
		navigationState.preserveChatDraft === true
	) {
		return "/chat";
	}
	if (pathname === "/settings" || pathname.startsWith("/settings/")) {
		return "settings";
	}

	if (
		pathname === "/user-settings" ||
		pathname.startsWith("/user-settings/")
	) {
		return "user-settings";
	}

	const isAppRoute = /^\/apps\/[^/]+(?:\/|$)/.test(pathname);
	const isAppEditorRoute = /^\/apps\/[^/]+\/edit(?:\/|$)/.test(pathname);
	const isAppRunnerRoute = isAppRoute && !isAppEditorRoute;
	return isAppRunnerRoute ? "app-runner" : pathname;
}
