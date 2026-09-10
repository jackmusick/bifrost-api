import type { BrowserContext, Route } from "@playwright/test";
import { promises as fs } from "node:fs";
import path from "node:path";

const MONACO_VERSION = "0.54.0";
const MONACO_ASSET_ROOT =
	process.env.PLAYWRIGHT_MONACO_ASSET_ROOT ??
	`/opt/monaco-cdn/monaco-editor-${MONACO_VERSION}/min/vs`;
const MONACO_CDN_BASE = `https://cdn.jsdelivr.net/npm/monaco-editor@${MONACO_VERSION}/min/vs`;
const MONACO_LOCAL_BASE = `/__e2e_monaco/${MONACO_VERSION}/min/vs`;

function resolveLocalAsset(assetPath: string) {
	const localPath = path.resolve(MONACO_ASSET_ROOT, assetPath);
	const assetRoot = path.resolve(MONACO_ASSET_ROOT);
	if (!localPath.startsWith(`${assetRoot}${path.sep}`)) {
		throw new Error(
			`Refusing Monaco asset path outside cache: ${assetPath}`,
		);
	}
	return localPath;
}

function loaderRewriteScript() {
	return `
;(() => {
	const expectedVs = ${JSON.stringify(MONACO_CDN_BASE)};
	const localVs = location.origin + ${JSON.stringify(MONACO_LOCAL_BASE)};
	const requireObject = window.require;
	if (!requireObject || typeof requireObject.config !== "function") {
		throw new Error("Monaco loader did not install window.require.config");
	}
	const originalConfig = requireObject.config.bind(requireObject);
	requireObject.config = (config) => {
		if (config?.paths?.vs === expectedVs) {
			config.paths.vs = localVs;
		} else if (config?.paths?.vs?.includes("monaco-editor@")) {
			throw new Error("Unexpected Monaco CDN path " + config.paths.vs + "; expected " + expectedVs);
		}
		return originalConfig(config);
	};
})();
`;
}

async function fulfillLoaderWithPathRewrite(route: Route) {
	const requestUrl = route.request().url();
	if (requestUrl !== `${MONACO_CDN_BASE}/loader.js`) {
		throw new Error(
			`Unexpected Monaco loader URL ${requestUrl}; expected ${MONACO_CDN_BASE}/loader.js`,
		);
	}
	const loader = await fs.readFile(resolveLocalAsset("loader.js"), "utf8");
	await route.fulfill({
		status: 200,
		headers: { "access-control-allow-origin": "*" },
		contentType: "application/javascript",
		body: `${loader}\n${loaderRewriteScript()}`,
	});
}

export async function routeMonacoAssets(context: BrowserContext) {
	await context.route(
		"https://cdn.jsdelivr.net/npm/monaco-editor@*/min/vs/loader.js",
		fulfillLoaderWithPathRewrite,
	);
}
