"""Synthetic design review workflow for isolated debug seeding."""

import asyncio
import logging

from bifrost import workflow

logger = logging.getLogger(__name__)


@workflow(
	name="design_review",
	description="Synthetic design review workflow for documentation and debug seeding",
	category="design_modernization",
	tags=["design", "review", "synthetic", "debug"],
)
async def design_review(
	review_id: str,
	summary: str,
	priority: str,
	owner: str,
	should_fail: bool = False,
) -> dict:
	logger.info(
		"Starting design review %s for owner=%s priority=%s should_fail=%s",
		review_id,
		owner,
		priority,
		should_fail,
	)
	for checkpoint in range(1, 5):
		await asyncio.sleep(2)
		logger.info("Review %s: checkpoint %s of 4", review_id, checkpoint)

	if should_fail:
		logger.info("Synthetic failure requested for %s", review_id)
		raise ValueError(f"Synthetic failure requested for {review_id}")

	result = {
		"review_id": review_id,
		"status": "success",
		"summary": summary,
		"priority": priority,
		"owner": owner,
		"message": f"Design review {review_id} completed successfully",
	}
	logger.info("Completed design review %s", review_id)
	return result
