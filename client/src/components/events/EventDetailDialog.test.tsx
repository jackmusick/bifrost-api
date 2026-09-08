/**
 * Component tests for EventDetailDialog.
 *
 * Covers the loading / not-found / populated branches. The embedded
 * DeliveriesTable + VariablesTreeView are stubbed — this spec is about the
 * dialog's composition, not those children.
 */

import { describe, it, expect, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";

const useEventMock = vi.fn();
const useDeliveriesMock = vi.fn();

vi.mock("@/services/events", async () => {
	const actual =
		await vi.importActual<typeof import("@/services/events")>(
			"@/services/events",
		);
	return {
		...actual,
		useEvent: (...args: unknown[]) => useEventMock(...args),
		useDeliveries: (...args: unknown[]) => useDeliveriesMock(...args),
	};
});

vi.mock("./DeliveriesTable", () => ({
	DeliveriesTable: () => <div data-marker="deliveries" />,
}));

vi.mock("@/components/ui/variables-tree-view", () => ({
	VariablesTreeView: ({ data }: { data: unknown }) => (
		<pre data-marker="variables-tree">{JSON.stringify(data)}</pre>
	),
}));

import { EventDetailDialog } from "./EventDetailDialog";
import type { Event } from "@/services/events";

function makeEvent(overrides: Partial<Event> = {}): Event {
	return {
		id: "evt-1",
		source_id: "src-1",
		event_type: "ticket.created",
		status: "completed",
		received_at: "2026-04-20T12:00:00Z",
		source_ip: "10.0.0.1",
		headers: { "X-Test": "1" },
		data: { hello: "world" },
		...overrides,
	} as unknown as Event;
}

describe("EventDetailDialog", () => {
	it("renders metadata when the event is loaded", () => {
		useEventMock.mockReturnValue({ data: makeEvent(), isLoading: false });
		useDeliveriesMock.mockReturnValue({
			data: { items: [], total: 0 },
			isLoading: false,
		});
		renderWithProviders(
			<EventDetailDialog event={makeEvent()} onClose={() => {}} />,
		);

		expect(screen.getByText("ticket.created")).toBeInTheDocument();
		expect(screen.getByText("Completed")).toBeInTheDocument();
		expect(screen.getByText("10.0.0.1")).toBeInTheDocument();
	});

	it("renders the not-found state when the event load returns null", () => {
		useEventMock.mockReturnValue({ data: null, isLoading: false });
		useDeliveriesMock.mockReturnValue({
			data: { items: [], total: 0 },
			isLoading: false,
		});
		renderWithProviders(
			<EventDetailDialog event={makeEvent()} onClose={() => {}} />,
		);
		expect(screen.getByText(/event not found/i)).toBeInTheDocument();
	});

	it("renders skeletons while loading", () => {
		useEventMock.mockReturnValue({ data: undefined, isLoading: true });
		useDeliveriesMock.mockReturnValue({
			data: { items: [], total: 0 },
			isLoading: false,
		});
		renderWithProviders(
			<EventDetailDialog event={makeEvent()} onClose={() => {}} />,
		);
		// Radix portals DialogContent outside the container — query from document.
		expect(document.querySelector(".animate-pulse")).toBeTruthy();
	});

	it("is hidden when event=null", () => {
		useEventMock.mockReturnValue({ data: undefined, isLoading: false });
		useDeliveriesMock.mockReturnValue({
			data: { items: [], total: 0 },
			isLoading: false,
		});
		renderWithProviders(
			<EventDetailDialog event={null} onClose={() => {}} />,
		);
		expect(
			screen.queryByRole("heading", { name: /event details/i }),
		).not.toBeInTheDocument();
	});

	it("opens from a deep-linked event id even when the list item is absent", () => {
		useEventMock.mockReturnValue({ data: undefined, isLoading: true });
		useDeliveriesMock.mockReturnValue({
			data: { items: [], total: 0 },
			isLoading: false,
		});
		renderWithProviders(
			<EventDetailDialog
				event={null}
				eventId="evt-deep"
				onClose={() => {}}
			/>,
		);
		expect(
			screen.getByRole("heading", { name: /event details/i }),
		).toBeInTheDocument();
		expect(document.querySelector(".animate-pulse")).toBeTruthy();
	});
});

describe("EventDetailDialog read recovery", () => {
	it("offers event retry rather than reporting a failed read as not found", async () => {
		const refetch = vi.fn();
		useEventMock.mockReturnValue({
			data: undefined,
			isError: true,
			isLoading: false,
			refetch,
		});
		useDeliveriesMock.mockReturnValue({
			data: undefined,
			isLoading: false,
		});
		const { user } = renderWithProviders(
			<EventDetailDialog event={makeEvent()} onClose={() => {}} />,
		);
		expect(screen.queryByText(/event not found/i)).not.toBeInTheDocument();
		await user.click(screen.getByRole("button", { name: "Retry event" }));
		expect(refetch).toHaveBeenCalledTimes(1);
	});
	it("keeps metadata and cached deliveries visible when refresh fails", async () => {
		const refetch = vi.fn();
		useEventMock.mockReturnValue({
			data: makeEvent(),
			isError: true,
			isLoading: false,
			refetch: vi.fn(),
		});
		useDeliveriesMock.mockReturnValue({
			data: { items: [], total: 3 },
			isError: true,
			isLoading: false,
			refetch,
		});
		const { user } = renderWithProviders(
			<EventDetailDialog event={makeEvent()} onClose={() => {}} />,
		);
		expect(screen.getByText("ticket.created")).toBeInTheDocument();
		expect(screen.getByText("Deliveries (3)")).toBeInTheDocument();
		expect(
			document.querySelector('[data-marker="deliveries"]'),
		).toBeTruthy();
		expect(screen.getAllByRole("alert")).toHaveLength(2);
		await user.click(
			screen.getByRole("button", { name: "Retry deliveries" }),
		);
		expect(refetch).toHaveBeenCalledTimes(1);
	});
	it("does not render an empty deliveries list or zero count when its read fails", () => {
		useEventMock.mockReturnValue({ data: makeEvent(), isLoading: false });
		useDeliveriesMock.mockReturnValue({
			data: undefined,
			isError: true,
			isLoading: false,
			refetch: vi.fn(),
		});
		renderWithProviders(
			<EventDetailDialog event={makeEvent()} onClose={() => {}} />,
		);
		expect(screen.getByRole("alert")).toHaveTextContent(
			"Could not load deliveries",
		);
		expect(screen.queryByText("Deliveries (0)")).not.toBeInTheDocument();
		expect(document.querySelector('[data-marker="deliveries"]')).toBeNull();
	});
});
