import { describe, expect, it } from "vitest";
import { failedMappings } from "./mapping-save";

describe("partial mapping retry", () => {
	const batch = [
		{ organization_id: "a", entity_id: "first" },
		{ organization_id: "b", entity_id: "second" },
	];
	it("retries only failed organizations and preserves their attempted values", () => {
		expect(
			failedMappings(batch, ["org b: provider rejected mapping"]),
		).toEqual([batch[1]]);
	});
	it("retains the batch when errors cannot identify an attempted organization", () => {
		expect(failedMappings(batch, ["Unexpected failure"])).toEqual(batch);
		expect(failedMappings(batch, ["org missing: rejected"])).toEqual(batch);
	});
});
