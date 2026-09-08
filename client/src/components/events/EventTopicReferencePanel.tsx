import { HelpSlideout } from "@/components/shared/HelpSlideout";
import type { TopicRegistryEntry } from "@/services/events";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";

const exampleTheme = {
	'code[class*="language-"]': {
		color: "var(--foreground)",
		background: "transparent",
		fontFamily: "var(--font-mono)",
	},
	'pre[class*="language-"]': {
		color: "var(--foreground)",
		background: "var(--muted)",
	},
	comment: { color: "var(--muted-foreground)" },
	keyword: { color: "var(--primary)", fontWeight: "600" },
	string: { color: "var(--bf-success)" },
	number: { color: "var(--bf-info)" },
	boolean: { color: "var(--bf-info)" },
};

type EventTopicReferenceTopic = TopicRegistryEntry & {
	category?: string;
	emitted_by?: string;
	example_body?: unknown;
};

interface EventTopicReferencePanelProps {
	topics: EventTopicReferenceTopic[];
}

const WORKFLOW_EXAMPLE = `from bifrost import workflow, context

@workflow(name="handle_builtin_event")
async def handle_builtin_event():
    event = context.event
    if event is None:
        return {"handled": False}

    event_id = event.id
    event_type = event.type
    body = event.data
    organization_id = event.organization_id
    received_at = event.received_at

    raw_event = context.parameters["_event"]
    headers = raw_event.get("headers") or {}
    source_ip = raw_event.get("source_ip")

    workflow_name = body.get("workflow", {}).get("name")
    return {"event_id": event_id, "event_type": event_type}`;

const INPUT_MAPPING_EXAMPLE = `workflow_name: "{{ _event.body.workflow.name }}"
error_message: "{{ _event.body.error.message }}"
event_type: "{{ _event.type }}"`;

function formatJson(value: unknown) {
	return JSON.stringify(value, null, 2);
}

function ExampleBlock({
	label,
	language,
	children,
}: {
	label: string;
	language: string;
	children: string;
}) {
	return (
		<div className="min-w-0 space-y-2">
			<h4 className="text-sm font-medium [overflow-wrap:anywhere]">
				{label}
			</h4>
			<SyntaxHighlighter
				language={language}
				style={exampleTheme}
				tabIndex={0}
				aria-label={`${label} code example`}
				wrapLongLines
				className="border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
				customStyle={{
					margin: 0,
					borderRadius: "var(--bf-radius-surface)",
					padding: "1rem",
					overflowWrap: "anywhere",
					whiteSpace: "pre-wrap",
					fontSize: "0.875rem",
					lineHeight: "1.5",
				}}
				codeTagProps={{
					style: {
						fontFamily: "var(--font-mono)",
						whiteSpace: "pre-wrap",
						overflowWrap: "anywhere",
					},
				}}
			>
				{children}
			</SyntaxHighlighter>
		</div>
	);
}

function TopicExample({ topic }: { topic: EventTopicReferenceTopic }) {
	return (
		<section className="min-w-0 space-y-3">
			<div className="space-y-1">
				<div className="flex min-w-0 flex-wrap items-center gap-2">
					<code className="min-w-0 rounded-[var(--bf-radius-control)] border bg-muted px-2 py-1 text-sm [overflow-wrap:anywhere]">
						{topic.topic}
					</code>
					<span className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
						{topic.category ?? "Built-in"}
					</span>
				</div>
				<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
					{topic.description}
				</p>
				<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
					Emitted by {topic.emitted_by ?? "Bifrost"}
				</p>
			</div>
			<ExampleBlock label={`${topic.topic} body`} language="json">
				{formatJson(topic.example_body ?? {})}
			</ExampleBlock>
		</section>
	);
}

export function EventTopicReferencePanel({
	topics,
}: EventTopicReferencePanelProps) {
	return (
		<HelpSlideout title="Event source reference">
			<section className="min-w-0 space-y-3">
				<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
					Event-triggered workflows can read a typed envelope from{" "}
					<code>context.event</code>. The same raw payload is
					available at{" "}
					<code>context.parameters["_event"]["body"]</code> for input
					mappings.
				</p>
				<ExampleBlock label="Python workflow access" language="python">
					{WORKFLOW_EXAMPLE}
				</ExampleBlock>
				<ExampleBlock label="Input mapping access" language="yaml">
					{INPUT_MAPPING_EXAMPLE}
				</ExampleBlock>
			</section>

			<section className="min-w-0 space-y-3">
				<div className="space-y-1">
					<h3 className="text-sm font-medium">Webhook envelope</h3>
					<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
						Webhooks expose adapter output as the event body, plus
						raw request metadata where available.
					</p>
				</div>
				<ExampleBlock label="_event envelope" language="json">
					{formatJson({
						id: "550e8400-e29b-41d4-a716-446655440000",
						type: "ticket.created",
						body: {
							ticket_id: "12345",
							status: "New",
						},
						headers: {
							"x-vendor-signature": "...",
						},
						received_at: "2026-05-28T12:34:56Z",
						source_ip: "203.0.113.10",
					})}
				</ExampleBlock>
			</section>

			<section className="space-y-5">
				<div className="space-y-1">
					<h3 className="text-sm font-medium">
						Built-in event bodies
					</h3>
					<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
						Built-in bodies use the same common keys:{" "}
						<code>schema_version</code>, <code>occurred_at</code>,{" "}
						<code>organization</code>, and <code>actor</code>.
					</p>
				</div>
				{topics.map((topic) => (
					<TopicExample key={topic.topic} topic={topic} />
				))}
			</section>
		</HelpSlideout>
	);
}
