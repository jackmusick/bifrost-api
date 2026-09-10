import { readFileSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export function validateLedger(ledger, readSpec) {
	const ids = new Set();
	for (const journey of ledger.journeys) {
		if (!journey.id || ids.has(journey.id))
			throw new Error(`Duplicate or missing journey ID: ${journey.id}`);
		ids.add(journey.id);
		if (!journey.title || !journey.area)
			throw new Error(`Incomplete journey: ${journey.id}`);
		for (const binding of journey.tests ?? []) {
			if (!binding.project || !binding.title || !binding.spec)
				throw new Error(`Incomplete binding: ${journey.id}`);
			if (
				!readSpec(binding.spec).includes(
					binding.sourceTitle ?? binding.title,
				)
			)
				throw new Error(
					`Missing test title in ${binding.spec}: ${binding.title}`,
				);
		}
	}
}

function collectTests(suites) {
	return (suites ?? []).flatMap((suite) => [
		...(suite.specs ?? []).flatMap((spec) =>
			spec.tests.map((test) => ({
				...test,
				title: spec.title,
				file: spec.file,
			})),
		),
		...collectTests(suite.suites),
	]);
}

export function buildReport(ledger, result) {
	const tests = collectTests(result?.suites);
	const rows = ledger.journeys.map((journey) => {
		const bindings = journey.tests ?? [];
		const cases = bindings.map((binding) => {
			const matches = tests.filter(
				(test) =>
					test.projectName === binding.project &&
					test.title === binding.title &&
					(test.file === binding.spec ||
						test.file.endsWith(`/${binding.spec}`)),
			);
			let status = "not run";
			if (matches.length > 0) {
				// Retries, unexpected passes, skipped tests and incomplete runs are
				// not accepted as proof of a successful user journey.
				status = matches.every(
					(test) =>
						test.status === "expected" &&
						test.expectedStatus === "passed" &&
						test.results.length === 1 &&
						test.results[0].status === "passed",
				)
					? "passed"
					: "failed or incomplete";
			}
			return { ...binding, status };
		});
		const status = !cases.length
			? "missing automation"
			: cases.some((item) => item.status === "failed or incomplete")
				? "failed or incomplete"
				: cases.every((item) => item.status === "passed")
					? "passed"
					: cases.some((item) => item.status === "passed")
						? "partially run"
						: "not run";
		return { ...journey, status, cases };
	});
	return {
		inventoryComplete: ledger.inventoryComplete,
		inventoryScope: ledger.inventoryScope,
		source: result?.config?.metadata ?? {},
		startedAt: result?.stats?.startTime ?? null,
		runErrors: result?.errors?.length ?? 0,
		suiteStats: result?.stats ?? null,
		rows,
	};
}

export function markdown(report) {
	const cell = (text) =>
		String(text).replaceAll("|", "\\|").replaceAll("\n", " ");
	return [
		"# UI acceptance evidence",
		"",
		`Source: ${report.source.sourceRevision ?? "unrecorded"}; dirty: ${report.source.sourceDirty ?? "unrecorded"}.`,
		`Run started: ${report.startedAt ?? "no results supplied"}. Run-level errors: ${report.runErrors}.`,
		`Whole run: ${report.suiteStats?.expected ?? 0} expected, ${report.suiteStats?.unexpected ?? 0} unexpected, ${report.suiteStats?.skipped ?? 0} skipped, ${report.suiteStats?.flaky ?? 0} flaky. Includes tests outside this ledger.`,
		"",
		report.inventoryComplete
			? "Inventory marked complete."
			: "**Inventory is incomplete. These tracked journeys are not a platform coverage percentage.**",
		...(report.inventoryScope ? [`Scope: ${report.inventoryScope}`] : []),
		"A passed row covers only its listed cases. Dirty/unrecorded runs are iteration evidence, not release sign-off.",
		"",
		"| Journey | Area | Result | Cases | Evidence type |",
		"| --- | --- | --- | --- | --- |",
		...report.rows.map(
			(row) =>
				`| ${cell(row.id)}: ${cell(row.title)} | ${cell(row.area)} | ${row.status} | ${row.cases.map((c) => `${cell(c.variant ?? c.project)}: ${c.status}`).join("; ") || "—"} | ${[...new Set(row.cases.map((c) => cell(c.proof ?? "unspecified")))].join("; ") || "—"} |`,
		),
		"",
	].join("\n");
}

if (
	process.argv[1] &&
	resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
	const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
	const ledger = JSON.parse(
		readFileSync(resolve(root, "e2e/acceptance-ledger.json"), "utf8"),
	);
	validateLedger(ledger, (spec) =>
		readFileSync(resolve(root, "e2e", spec), "utf8"),
	);
	const resultsPath = process.argv[2];
	if (resultsPath && !existsSync(resultsPath))
		throw new Error(`Results file does not exist: ${resultsPath}`);
	const results = resultsPath
		? JSON.parse(readFileSync(resultsPath, "utf8"))
		: null;
	process.stdout.write(markdown(buildReport(ledger, results)));
}
