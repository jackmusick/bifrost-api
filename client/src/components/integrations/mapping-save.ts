export interface MappingSaveInput {
	organization_id: string;
	entity_id: string;
	entity_name?: string;
}

/** The batch endpoint identifies failed organizations as `org <id>: <message>`. */
export function failedMappings(
	batch: MappingSaveInput[],
	errors: string[],
): MappingSaveInput[] {
	const failedIds = errors.map((error) => /^org ([^:]+):/.exec(error)?.[1]);
	// Preserve a retry path if a future server returns an unrecognized error shape.
	if (
		failedIds.some(
			(id) => !id || !batch.some((item) => item.organization_id === id),
		)
	)
		return batch;
	return batch.filter((item) => failedIds.includes(item.organization_id));
}
