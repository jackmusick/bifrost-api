import { describe, expect, it } from "vitest";
import { serializeReportCSV } from "./report-csv";

describe("report CSV", () => {
	it("preserves commas, quotes, line breaks, Unicode and numeric zero in exported records", () => {
		expect(
			serializeReportCSV([
				["Name", "Value"],
				['Northwind, "Support"', 0],
				["Line one\nLine two — 東京", 1.25],
			]),
		).toBe(
			'Name,Value\n"Northwind, ""Support""",0\n"Line one\nLine two — 東京",1.25',
		);
	});
});
