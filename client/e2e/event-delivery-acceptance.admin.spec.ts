/**
 * Event delivery acceptance (Admin)
 *
 * Creates a local generic webhook source and workflow subscription through the
 * API, sends a webhook, then proves the event/delivery outcome through the UI.
 */

import { expect, test } from "./fixtures/api-fixture";
import type { AuthedApi } from "./fixtures/api-fixture";

const UNIQUE = `${Date.now()}_${Math.floor(Math.random() * 10000)}`;
const WORKFLOW_PATH = `e2e_event_delivery_acceptance_${UNIQUE}.py`;
const WORKFLOW_FUNCTION = `e2e_event_delivery_acceptance_${UNIQUE}`;
const SOURCE_NAME = `E2E Event Delivery ${UNIQUE}`;
const EVENT_TYPE = `event.acceptance.${UNIQUE}`;
const PAYLOAD_MARKER = `event-payload-${UNIQUE}`;
const RESULT_MARKER = `event-result-${UNIQUE}`;
const WORKFLOW_CONTENT = `"""E2E event delivery acceptance workflow ${UNIQUE}"""
from bifrost import workflow

@workflow(
    name="${WORKFLOW_FUNCTION}",
    description="E2E event delivery acceptance Playwright fixture",
)
async def ${WORKFLOW_FUNCTION}(event_type: str = "", marker: str = "", _event: dict | None = None) -> dict:
    return {
        "event_type": event_type,
        "marker": marker,
        "result_marker": "${RESULT_MARKER}",
        "event_id": (_event or {}).get("id"),
    }
`;

type EventRecord = {
	id: string;
	event_type: string | null;
	status: string;
	data?: Record<string, unknown>;
	success_count: number;
	delivery_count: number;
};

type DeliveryRecord = {
	id: string | null;
	status: string;
	workflow_name: string | null;
	execution_id: string | null;
};

async function registerWorkflow(api: AuthedApi) {
	const writeResp = await api.put("/api/files/editor/content", {
		data: {
			path: WORKFLOW_PATH,
			content: WORKFLOW_CONTENT,
			encoding: "utf-8",
		},
	});
	expect(writeResp.ok(), await writeResp.text()).toBe(true);

	const registerResp = await api.post("/api/workflows/register", {
		data: { path: WORKFLOW_PATH, function_name: WORKFLOW_FUNCTION },
	});
	expect(registerResp.ok(), await registerResp.text()).toBe(true);
	const workflow = (await registerResp.json()) as { id: string };
	expect(workflow.id).toBeTruthy();
	return workflow.id;
}

async function createWebhookSource(api: AuthedApi) {
	const response = await api.post("/api/events/sources", {
		data: {
			name: SOURCE_NAME,
			source_type: "webhook",
			organization_id: null,
			webhook: {
				adapter_name: "generic",
				config: {
					event_type_field: "event_type",
				},
			},
		},
	});
	expect(response.ok(), await response.text()).toBe(true);
	const source = (await response.json()) as { id: string };
	expect(source.id).toBeTruthy();
	return source.id;
}

async function createSubscription(
	api: AuthedApi,
	sourceId: string,
	workflowId: string,
) {
	const response = await api.post(
		`/api/events/sources/${sourceId}/subscriptions`,
		{
			data: {
				target_type: "workflow",
				workflow_id: workflowId,
				event_type: EVENT_TYPE,
			},
		},
	);
	expect(response.ok(), await response.text()).toBe(true);
}

async function sendWebhook(api: AuthedApi, sourceId: string) {
	const response = await api.post(`/api/hooks/${sourceId}`, {
		data: {
			event_type: EVENT_TYPE,
			marker: PAYLOAD_MARKER,
		},
		headers: { "Content-Type": "application/json" },
	});
	expect(response.status(), await response.text()).toBe(202);
}

async function getEvent(api: AuthedApi, sourceId: string) {
	const response = await api.get(`/api/events/sources/${sourceId}/events`, {
		params: { event_type: EVENT_TYPE, limit: 100 },
	});
	expect(response.ok(), await response.text()).toBe(true);
	const body = (await response.json()) as { items: EventRecord[] };
	return body.items.find(
		(event) =>
			event.event_type === EVENT_TYPE &&
			event.data?.marker === PAYLOAD_MARKER,
	);
}

async function getDeliveries(api: AuthedApi, eventId: string) {
	const response = await api.get(`/api/events/${eventId}/deliveries`);
	expect(response.ok(), await response.text()).toBe(true);
	const body = (await response.json()) as { items: DeliveryRecord[] };
	return body.items;
}

async function waitForSuccessfulDelivery(api: AuthedApi, sourceId: string) {
	const startedAt = Date.now();
	let lastStatus = "no event";

	for (;;) {
		const event = await getEvent(api, sourceId);
		if (event) {
			const deliveries = await getDeliveries(api, event.id);
			const delivery = deliveries.find(
				(candidate) => candidate.workflow_name === WORKFLOW_FUNCTION,
			);
			if (delivery) {
				lastStatus = `${event.status}/${delivery.status}`;
				if (delivery.status === "success" && delivery.execution_id) {
					return { event, delivery };
				}
			} else {
				lastStatus = `${event.status}/no matching delivery`;
			}
		}

		if (Date.now() - startedAt > 60_000) {
			throw new Error(
				`Event ${EVENT_TYPE} did not reach successful delivery; last status ${lastStatus}`,
			);
		}
		await new Promise((resolve) => setTimeout(resolve, 500));
	}
}

async function waitForEventAggregate(api: AuthedApi, sourceId: string) {
	const startedAt = Date.now();
	let lastStatus = "no event";

	for (;;) {
		const event = await getEvent(api, sourceId);
		if (event) {
			lastStatus = `${event.status}/${event.success_count}/${event.delivery_count}`;
			if (
				event.status.toLowerCase() === "completed" &&
				event.success_count === 1 &&
				event.delivery_count === 1
			) {
				return event;
			}
		}

		if (Date.now() - startedAt > 30_000) {
			throw new Error(
				`Event ${EVENT_TYPE} aggregate did not settle; last status ${lastStatus}`,
			);
		}
		await new Promise((resolve) => setTimeout(resolve, 500));
	}
}

test("[EVENT-01 desktop] local webhook event shows successful workflow delivery and execution outcome", async ({
	page,
	api,
	context,
}) => {
	const workflowId = await registerWorkflow(api);
	const sourceId = await createWebhookSource(api);

	try {
		await createSubscription(api, sourceId, workflowId);
		await sendWebhook(api, sourceId);
		const { event, delivery } = await waitForSuccessfulDelivery(
			api,
			sourceId,
		);

		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto("/event-sources");
		await expect(
			page.getByRole("heading", { name: "Event Sources" }),
		).toBeVisible({ timeout: 10_000 });
		await page.getByLabel("Search event sources...").fill(SOURCE_NAME);
		await page.getByRole("link", { name: SOURCE_NAME }).click();
		await expect(
			page.getByRole("heading", { level: 1, name: SOURCE_NAME }),
		).toBeVisible({ timeout: 10_000 });
		await expect(page.getByText("1 subscription")).toBeVisible();

		await page.getByRole("tab", { name: "Events" }).click();
		await page.getByLabel("Search events").fill(EVENT_TYPE);
		const eventRow = page.getByRole("row", {
			name: new RegExp(EVENT_TYPE),
		});
		await expect(eventRow).toBeVisible({ timeout: 10_000 });
		await expect(eventRow).toContainText("Completed");
		await expect(eventRow).toContainText("1 total");
		await expect(eventRow).toContainText("1 ok");
		await eventRow.getByRole("link", { name: EVENT_TYPE }).click();

		const eventDialog = page.getByRole("dialog", { name: "Event Details" });
		await expect(eventDialog).toBeVisible({ timeout: 10_000 });
		await expect(eventDialog).toContainText(PAYLOAD_MARKER);
		await expect(eventDialog).toContainText(WORKFLOW_FUNCTION);
		await expect(eventDialog).toContainText("Success");
		await expect(eventDialog).toContainText("1 attempt");

		const executionPagePromise = context.waitForEvent("page");
		await eventDialog
			.getByRole("link", { name: /view execution/i })
			.click();
		const executionPage = await executionPagePromise;
		await executionPage.waitForLoadState("domcontentloaded");
		await expect(executionPage).toHaveURL(
			new RegExp(`/history/${delivery.execution_id}$`),
		);
		await expect(
			executionPage.getByRole("heading", {
				level: 1,
				name: WORKFLOW_FUNCTION,
			}),
		).toBeVisible({ timeout: 10_000 });
		await expect(
			executionPage.getByText("Completed", { exact: true }),
		).toBeVisible();
		await expect(
			executionPage.getByRole("tabpanel", {
				name: "Result",
				exact: true,
			}),
		).toContainText(RESULT_MARKER);

		const settledEvent = await waitForEventAggregate(api, sourceId);
		expect(settledEvent.id).toBe(event.id);
		expect(settledEvent.success_count).toBe(1);
		expect(settledEvent.delivery_count).toBe(1);
		expect(delivery.execution_id).toBeTruthy();
	} finally {
		expect([200, 204, 404]).toContain(
			(await api.delete(`/api/events/sources/${sourceId}`)).status(),
		);
		expect([200, 204, 404]).toContain(
			(
				await api.delete(
					`/api/files/editor?path=${encodeURIComponent(WORKFLOW_PATH)}`,
				)
			).status(),
		);
	}
});
