import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
	createMonacoAssetHandler,
	monacoMountPrefix,
} from "./monaco-assets.mjs";

async function withServer(assetRoot, callback) {
	let fellThrough = 0;
	const handler = createMonacoAssetHandler({ assetRoot });
	const server = http.createServer((request, response) => {
		if (handler(request, response)) return;
		fellThrough += 1;
		response.writeHead(418, { "content-type": "text/plain" });
		response.end("fell through");
	});
	await new Promise((resolve, reject) => {
		server.once("error", reject);
		server.listen(0, "127.0.0.1", resolve);
	});
	const address = server.address();
	assert.equal(typeof address, "object");
	try {
		return await callback({
			baseUrl: `http://127.0.0.1:${address.port}`,
			get fellThrough() {
				return fellThrough;
			},
		});
	} finally {
		await new Promise((resolve, reject) =>
			server.close((error) => (error ? reject(error) : resolve())),
		);
	}
}

async function makeAssetRoot(t) {
	const root = await mkdtemp(join(tmpdir(), "monaco-assets-"));
	t.after(() => rm(root, { recursive: true, force: true }));
	await writeFile(
		join(root, "editor.main.js"),
		"self.editorLoaded = true;\n",
	);
	await writeFile(
		join(root, "ts.worker-C4E4vgbE.js"),
		Buffer.from([0, 1, 2, 3, 255]),
	);
	return root;
}

test("serves JavaScript and binary worker assets", async (t) => {
	const root = await makeAssetRoot(t);
	await withServer(root, async ({ baseUrl }) => {
		const js = await fetch(`${baseUrl}${monacoMountPrefix}editor.main.js`);
		assert.equal(js.status, 200);
		assert.equal(js.headers.get("content-type"), "application/javascript");
		assert.equal(js.headers.get("access-control-allow-origin"), "*");
		assert.match(await js.text(), /editorLoaded/);

		const worker = await fetch(
			`${baseUrl}${monacoMountPrefix}ts.worker-C4E4vgbE.js`,
		);
		assert.equal(worker.status, 200);
		assert.equal(
			worker.headers.get("content-type"),
			"application/javascript",
		);
		assert.deepEqual(
			Buffer.from(await worker.arrayBuffer()),
			Buffer.from([0, 1, 2, 3, 255]),
		);
	});
});

test("returns 404 for missing files", async (t) => {
	const root = await makeAssetRoot(t);
	await withServer(root, async ({ baseUrl }) => {
		const response = await fetch(
			`${baseUrl}${monacoMountPrefix}missing.js`,
		);
		assert.equal(response.status, 404);
		assert.equal(await response.text(), "Monaco asset not found");
	});
});

test("denies encoded traversal", async (t) => {
	const root = await makeAssetRoot(t);
	await withServer(root, async ({ baseUrl }) => {
		const response = await fetch(
			`${baseUrl}${monacoMountPrefix}%2E%2E%2Fsecret.js`,
		);
		assert.equal(response.status, 400);
		assert.equal(await response.text(), "Invalid Monaco asset path");
	});
});

test("malformed encoded paths return 400 without crashing", async (t) => {
	const root = await makeAssetRoot(t);
	await withServer(root, async ({ baseUrl }) => {
		const response = await fetch(`${baseUrl}${monacoMountPrefix}%E0%A4%A`);
		assert.equal(response.status, 400);
		assert.equal(await response.text(), "Invalid Monaco asset path");
	});
});

test("unrelated URLs fall through", async (t) => {
	const root = await makeAssetRoot(t);
	await withServer(root, async (server) => {
		const response = await fetch(`${server.baseUrl}/assets/app.js`);
		assert.equal(response.status, 418);
		assert.equal(await response.text(), "fell through");
		assert.equal(server.fellThrough, 1);
	});
});
