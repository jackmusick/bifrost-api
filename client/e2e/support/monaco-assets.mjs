import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, resolve, sep } from "node:path";

export const monacoVersion = "0.54.0";
export const monacoMountPrefix = `/__e2e_monaco/${monacoVersion}/min/vs/`;
export const defaultMonacoAssetRoot = `/opt/monaco-cdn/monaco-editor-${monacoVersion}/min/vs`;

function contentTypeFor(filePath) {
	switch (extname(filePath)) {
		case ".js":
			return "application/javascript";
		case ".css":
			return "text/css";
		case ".json":
		case ".map":
			return "application/json";
		case ".ttf":
			return "font/ttf";
		case ".woff":
			return "font/woff";
		case ".woff2":
			return "font/woff2";
		default:
			return "application/octet-stream";
	}
}

function sendText(response, status, body) {
	response.writeHead(status, { "content-type": "text/plain" });
	response.end(body);
}

export function createMonacoAssetHandler({
	assetRoot = defaultMonacoAssetRoot,
} = {}) {
	const resolvedAssetRoot = resolve(assetRoot);

	return function tryServeMonacoAsset(request, response) {
		let requestUrl;
		try {
			requestUrl = new URL(request.url || "/", "http://127.0.0.1");
		} catch {
			return false;
		}

		if (!requestUrl.pathname.startsWith(monacoMountPrefix)) {
			return false;
		}

		let relativeAssetPath;
		try {
			relativeAssetPath = decodeURIComponent(
				requestUrl.pathname.slice(monacoMountPrefix.length),
			);
		} catch {
			sendText(response, 400, "Invalid Monaco asset path");
			return true;
		}

		const localPath = resolve(resolvedAssetRoot, relativeAssetPath);
		if (
			localPath !== resolvedAssetRoot &&
			!localPath.startsWith(`${resolvedAssetRoot}${sep}`)
		) {
			sendText(response, 400, "Invalid Monaco asset path");
			return true;
		}

		let fileStat;
		try {
			if (!existsSync(localPath)) {
				sendText(response, 404, "Monaco asset not found");
				return true;
			}
			fileStat = statSync(localPath);
		} catch {
			sendText(response, 404, "Monaco asset not found");
			return true;
		}
		if (!fileStat.isFile()) {
			sendText(response, 404, "Monaco asset not found");
			return true;
		}

		response.writeHead(200, {
			"access-control-allow-origin": "*",
			"cache-control": "public, max-age=31536000, immutable",
			"content-type": contentTypeFor(localPath),
		});

		const stream = createReadStream(localPath);
		stream.on("error", () => {
			if (!response.headersSent) {
				sendText(response, 404, "Monaco asset not found");
			} else {
				response.destroy();
			}
		});
		stream.pipe(response);
		return true;
	};
}
