import { test } from "node:test";
import assert from "node:assert/strict";
import { buildReport, markdown, validateLedger } from "./acceptance-report.mjs";

const binding = {
	spec: "form.admin.spec.ts",
	title: "[FORM-01] submit",
	project: "platform-admin",
};
const ledger = {
	inventoryComplete: false,
	journeys: [
		{ id: "FORM-01", area: "Forms", title: "Submit", tests: [binding] },
		{ id: "FORM-02", area: "Forms", title: "Edit", tests: [] },
	],
};
function result(test = {}) {
	return {
		config: {
			metadata: { sourceRevision: "candidate", sourceDirty: "true" },
		},
		suites: [
			{
				suites: [
					{
						specs: [
							{
								file: binding.spec,
								title: binding.title,
								tests: [
									{
										projectName: binding.project,
										expectedStatus: "passed",
										status: "expected",
										results: [{ status: "passed" }],
										...test,
									},
								],
							},
						],
					},
				],
			},
		],
	};
}

test("joins nested results by exact file/title/project and preserves missing work", () => {
	const report = buildReport(ledger, result());
	assert.deepEqual(
		report.rows.map((row) => row.status),
		["passed", "missing automation"],
	);
	assert.equal(report.source.sourceRevision, "candidate");
	assert.equal(report.inventoryComplete, false);
	assert.equal(
		buildReport(ledger, result({ projectName: "org-user" })).rows[0].status,
		"not run",
	);
});

test("skips, retries, expected failures and interruptions never become passing evidence", () => {
	for (const override of [
		{ results: [{ status: "skipped" }] },
		{ results: [{ status: "failed" }, { status: "passed" }] },
		{ expectedStatus: "failed", results: [{ status: "failed" }] },
		{ results: [] },
		{ status: "unexpected" },
	])
		assert.equal(
			buildReport(ledger, result(override)).rows[0].status,
			"failed or incomplete",
		);
});

test("a desktop pass cannot hide an unrun mobile case or run-level error", () => {
	const both = structuredClone(ledger);
	both.journeys[0].tests.push({
		...binding,
		title: "[FORM-01] mobile submit",
	});
	const data = result();
	data.errors = [{ message: "setup failure" }];
	const report = buildReport(both, data);
	assert.equal(report.rows[0].status, "partially run");
	assert.equal(report.runErrors, 1);
	assert.equal(buildReport(ledger, null).rows[0].status, "not run");
});

test("invalid ledger references fail loudly", () => {
	assert.doesNotThrow(() => validateLedger(ledger, () => binding.title));
	assert.throws(
		() => validateLedger(ledger, () => "renamed test"),
		/Missing test title/,
	);
	assert.throws(
		() =>
			validateLedger(
				{ journeys: [...ledger.journeys, ledger.journeys[0]] },
				() => binding.title,
			),
		/Duplicate/,
	);
});

test("whole-run failures remain visible even when all bound cases pass", () => {
	const data = result();
	data.stats = { expected: 1, unexpected: 1, skipped: 2, flaky: 0 };
	const report = buildReport(ledger, data);
	assert.equal(report.rows[0].status, "passed");
	assert.match(
		markdown(report),
		/1 expected, 1 unexpected, 2 skipped, 0 flaky/,
	);
});

test("rendered evidence distinguishes controlled setup from real platform journeys", () => {
	const mixed = {
		...ledger,
		journeys: [
			{
				...ledger.journeys[0],
				tests: [{ ...binding, proof: "mixed-setup-real-mutation" }],
			},
		],
	};
	const output = markdown(buildReport(mixed, result()));
	assert.match(output, /Evidence type/);
	assert.match(output, /mixed-setup-real-mutation/);
});
