import { StrictMode, useState } from "react";
import { describe, expect, it } from "vitest";

import { renderWithProviders, screen } from "@/test-utils";

import { DidNarrative } from "./DidNarrative";

describe("DidNarrative", () => {
	it("preserves the action link while its preview updates the parent", async () => {
		const activate = vi.fn();
		function PreviewHarness() {
			const [preview, setPreview] = useState<string | null>(null);
			return (
				<div aria-label={preview ?? "No preview"}>
					<DidNarrative
						text="Used [send_email]."
						activityReferences={{
							send_email: [
								{ activityId: "sent", label: "Sent email" },
							],
						}}
						onReferencePreview={setPreview}
						onReferenceActivate={activate}
					/>
				</div>
			);
		}
		const { user } = renderWithProviders(
			<StrictMode>
				<PreviewHarness />
			</StrictMode>,
		);
		const link = screen.getByRole("link", {
			name: "Show Sent email in Activity",
		});
		await user.hover(link);
		expect(
			screen.getByRole("link", { name: "Show Sent email in Activity" }),
		).toBe(link);
		await user.click(link);
		expect(activate).toHaveBeenCalledWith("sent");
	});
	it("formats prose while preserving real links and code containing marker-like text", () => {
		renderWithProviders(
			<DidNarrative
				text={
					"### Outcome\n\n**Reviewed** [send_email]. Read [guide](https://example.com) and keep `[literal_code]`."
				}
			/>,
		);
		expect(
			screen.getByRole("heading", { name: "Outcome" }),
		).toBeInTheDocument();
		expect(screen.getByRole("link", { name: "guide" })).toHaveAttribute(
			"href",
			"https://example.com",
		);
		expect(screen.getByText("[literal_code]")).toBeInTheDocument();
		expect(screen.getByText("Send email")).toBeInTheDocument();
	});
	it("replaces machine markers with quiet human-readable references", () => {
		renderWithProviders(
			<DidNarrative text="I used [ai_ticketing_get_ticket_details] to fetch the ticket." />,
		);

		expect(screen.getByText("Get ticket details")).toBeInTheDocument();
		expect(
			screen.queryByText("ai_ticketing_get_ticket_details"),
		).not.toBeInTheDocument();
		expect(screen.queryByRole("link")).not.toBeInTheDocument();
	});

	it("links a verified marker to its recorded activity and previews it on hover", async () => {
		const onPreview = vi.fn();
		const onActivate = vi.fn();
		const { user } = renderWithProviders(
			<DidNarrative
				text="Then [send_email] confirmed the update."
				activityReferences={{
					send_email: [
						{
							activityId: "activity-1",
							label: "Sent email",
						},
					],
				}}
				onReferencePreview={onPreview}
				onReferenceActivate={onActivate}
			/>,
		);

		const reference = screen.getByRole("link", {
			name: "Show Sent email in Activity",
		});
		expect(reference).toHaveAttribute(
			"href",
			"#run-activity-item-activity-1",
		);

		await user.hover(reference);
		expect(onPreview).toHaveBeenLastCalledWith("activity-1");
		await user.unhover(reference);
		expect(onPreview).toHaveBeenLastCalledWith(null);
		await user.click(reference);
		expect(onActivate).toHaveBeenCalledWith("activity-1");
	});

	it("uses the recorded child agent name for delegation references", () => {
		renderWithProviders(
			<DidNarrative
				text="I asked [delegate_to_troubleshooting_agent] to investigate."
				activityReferences={{
					delegate_to_troubleshooting_agent: [
						{
							activityId: "delegation-1",
							label: "Troubleshooting Specialist",
						},
					],
				}}
				onReferenceActivate={() => {}}
			/>,
		);

		const reference = screen.getByText("Troubleshooting Specialist");
		expect(reference).toHaveAttribute("data-slot", "activity-reference");
		expect(
			screen.queryByText("delegate_to_troubleshooting_agent"),
		).not.toBeInTheDocument();
	});

	it("uses a neutral delegation label when no child run was recorded", () => {
		renderWithProviders(
			<DidNarrative text="I asked [delegate_to_missing_agent] to investigate." />,
		);
		expect(screen.getByText("Delegated agent")).toBeInTheDocument();
		expect(screen.queryByText("Missing Agent")).not.toBeInTheDocument();
		expect(screen.queryByRole("link")).not.toBeInTheDocument();
	});

	it("returns the fallback when text is empty", () => {
		renderWithProviders(
			<DidNarrative
				text={null}
				fallback={<span data-testid="fallback">No summary</span>}
			/>,
		);
		expect(screen.getByTestId("fallback")).toBeInTheDocument();
	});

	it("pairs repeated markers with recorded activity occurrences in order", () => {
		const { container } = renderWithProviders(
			<DidNarrative
				text="First [search_knowledge], then [search_knowledge]."
				activityReferences={{
					search_knowledge: [
						{ activityId: "search-1", label: "Searched knowledge" },
						{ activityId: "search-2", label: "Searched knowledge" },
					],
				}}
				onReferenceActivate={() => {}}
			/>,
		);
		const references = Array.from(
			container.querySelectorAll('[data-slot="activity-reference"]'),
		).map((element) => element.getAttribute("data-activity-reference-id"));
		expect(references).toEqual(["search-1", "search-2"]);
	});
});
