import { format, parseISO } from "date-fns";
import type {
	UsageReportResponse,
	UsageSource,
	WorkflowUsage,
	ConversationUsage,
	UsageTrend,
} from "@/services/usage";

type DemoWorkflowUsage = WorkflowUsage & { organization_id: string };
type DemoConversationUsage = ConversationUsage & { organization_id: string };
type DemoAgentUsage = NonNullable<UsageReportResponse["by_agent"]>[number] & {
	organization_id: string;
};

const DEMO_WORKFLOW_TEMPLATES = [
	{
		name: "User Onboarding",
		inputTokens: 45000,
		outputTokens: 12000,
		cost: 0.85,
		cpuSeconds: 120,
		memoryBytes: 256 * 1024 * 1024,
		baseCount: 280,
	},
	{
		name: "Ticket Triage",
		inputTokens: 22000,
		outputTokens: 8000,
		cost: 0.42,
		cpuSeconds: 45,
		memoryBytes: 128 * 1024 * 1024,
		baseCount: 450,
	},
	{
		name: "Invoice Processing",
		inputTokens: 35000,
		outputTokens: 15000,
		cost: 0.68,
		cpuSeconds: 90,
		memoryBytes: 192 * 1024 * 1024,
		baseCount: 190,
	},
	{
		name: "Compliance Check",
		inputTokens: 78000,
		outputTokens: 25000,
		cost: 1.45,
		cpuSeconds: 180,
		memoryBytes: 384 * 1024 * 1024,
		baseCount: 75,
	},
	{
		name: "Data Backup Verification",
		inputTokens: 18000,
		outputTokens: 5000,
		cost: 0.32,
		cpuSeconds: 60,
		memoryBytes: 96 * 1024 * 1024,
		baseCount: 210,
	},
	{
		name: "Report Generation",
		inputTokens: 55000,
		outputTokens: 30000,
		cost: 1.12,
		cpuSeconds: 150,
		memoryBytes: 320 * 1024 * 1024,
		baseCount: 70,
	},
];

const DEMO_CONVERSATION_TEMPLATES = [
	{
		title: "Help with deployment",
		messages: 12,
		inputTokens: 8500,
		outputTokens: 4200,
		cost: 0.18,
	},
	{
		title: "Database migration questions",
		messages: 8,
		inputTokens: 5200,
		outputTokens: 3100,
		cost: 0.12,
	},
	{
		title: "API integration support",
		messages: 15,
		inputTokens: 11000,
		outputTokens: 6500,
		cost: 0.25,
	},
	{
		title: "Security audit discussion",
		messages: 6,
		inputTokens: 4000,
		outputTokens: 2200,
		cost: 0.09,
	},
	{
		title: "Performance optimization",
		messages: 10,
		inputTokens: 7500,
		outputTokens: 4800,
		cost: 0.17,
	},
	{
		title: "New feature planning",
		messages: 20,
		inputTokens: 15000,
		outputTokens: 9000,
		cost: 0.34,
	},
];

const DEMO_AGENT_TEMPLATES = [
	{
		name: "Triage Router",
		inputTokens: 18000,
		outputTokens: 6000,
		cost: 0.34,
		cpuSeconds: 40,
		memoryBytes: 96 * 1024 * 1024,
		baseCount: 360,
	},
	{
		name: "Support Escalation",
		inputTokens: 14000,
		outputTokens: 5000,
		cost: 0.29,
		cpuSeconds: 55,
		memoryBytes: 128 * 1024 * 1024,
		baseCount: 220,
	},
	{
		name: "Research Assistant",
		inputTokens: 26000,
		outputTokens: 12000,
		cost: 0.52,
		cpuSeconds: 70,
		memoryBytes: 160 * 1024 * 1024,
		baseCount: 180,
	},
	{
		name: "Policy Reviewer",
		inputTokens: 30000,
		outputTokens: 9000,
		cost: 0.61,
		cpuSeconds: 80,
		memoryBytes: 192 * 1024 * 1024,
		baseCount: 140,
	},
	{
		name: "Meeting Synthesizer",
		inputTokens: 12000,
		outputTokens: 7000,
		cost: 0.24,
		cpuSeconds: 35,
		memoryBytes: 80 * 1024 * 1024,
		baseCount: 260,
	},
	{
		name: "Workflow Builder",
		inputTokens: 42000,
		outputTokens: 15000,
		cost: 0.78,
		cpuSeconds: 95,
		memoryBytes: 256 * 1024 * 1024,
		baseCount: 90,
	},
];

const FALLBACK_DEMO_ORGS = [
	{ id: "demo-org-1", name: "Acme Corp" },
	{ id: "demo-org-2", name: "TechStart Inc" },
	{ id: "demo-org-3", name: "Global Services LLC" },
];

export interface UsageDemoDataParams {
	startDate: string;
	endDate: string;
	orgId: string | null;
	source: UsageSource;
	realOrgs: Array<{ id: string; name: string }> | undefined;
}

function pickOrg(orgs: Array<{ id: string; name: string }>, index: number) {
	return orgs[index % orgs.length];
}

export function generateUsageDemoData(
	params: UsageDemoDataParams,
): UsageReportResponse {
	const { startDate, endDate, orgId, source, realOrgs } = params;
	const orgs =
		realOrgs && realOrgs.length > 0 ? realOrgs : FALLBACK_DEMO_ORGS;

	const allWorkflows: DemoWorkflowUsage[] = DEMO_WORKFLOW_TEMPLATES.map(
		(template, index) => {
			const org = pickOrg(orgs, index);
			const variance = 0.9 + Math.random() * 0.2;
			const executions = Math.floor(template.baseCount * variance);

			return {
				workflow_name: template.name,
				organization_id: org.id,
				execution_count: executions,
				input_tokens: Math.floor(
					template.inputTokens * executions * variance,
				),
				output_tokens: Math.floor(
					template.outputTokens * executions * variance,
				),
				ai_cost: (template.cost * executions * variance).toFixed(2),
				cpu_seconds: Math.floor(
					template.cpuSeconds * executions * variance,
				),
				memory_bytes: template.memoryBytes,
			};
		},
	);

	const allConversations: DemoConversationUsage[] =
		DEMO_CONVERSATION_TEMPLATES.map((template, index) => {
			const org = pickOrg(orgs, index);
			const variance = 0.85 + Math.random() * 0.3;

			return {
				conversation_id: `demo-conv-${index + 1}`,
				conversation_title: template.title,
				organization_id: org.id,
				message_count: Math.floor(template.messages * variance),
				input_tokens: Math.floor(template.inputTokens * variance),
				output_tokens: Math.floor(template.outputTokens * variance),
				ai_cost: (template.cost * variance).toFixed(2),
			};
		});

	const allAgents: DemoAgentUsage[] = DEMO_AGENT_TEMPLATES.map(
		(template, index) => {
			const org = pickOrg(orgs, index);
			const variance = 0.9 + Math.random() * 0.25;
			const runCount = Math.floor(template.baseCount * variance);

			return {
				agent_name: template.name,
				run_count: runCount,
				input_tokens: Math.floor(
					template.inputTokens * runCount * variance,
				),
				output_tokens: Math.floor(
					template.outputTokens * runCount * variance,
				),
				ai_cost: (template.cost * runCount * variance).toFixed(2),
				organization_id: org.id,
			};
		},
	);

	const filteredWorkflows = orgId
		? allWorkflows.filter((workflow) => workflow.organization_id === orgId)
		: allWorkflows;
	const filteredConversations = orgId
		? allConversations.filter(
				(conversation) => conversation.organization_id === orgId,
			)
		: allConversations;
	const filteredAgents = orgId
		? allAgents.filter((agent) => agent.organization_id === orgId)
		: allAgents;

	const includeWorkflows = source === "all" || source === "executions";
	const includeConversations = source === "all" || source === "chat";
	const includeAgents = source === "all" || source === "agents";

	let totalInputTokens = 0;
	let totalOutputTokens = 0;
	let totalAiCost = 0;
	let totalCpuSeconds = 0;
	let peakMemoryBytes = 0;
	let totalAiCalls = 0;

	if (includeWorkflows) {
		for (const workflow of filteredWorkflows) {
			totalInputTokens += workflow.input_tokens;
			totalOutputTokens += workflow.output_tokens;
			totalAiCost += parseFloat(workflow.ai_cost || "0");
			totalCpuSeconds += workflow.cpu_seconds;
			peakMemoryBytes = Math.max(peakMemoryBytes, workflow.memory_bytes);
			totalAiCalls += workflow.execution_count;
		}
	}

	if (includeConversations) {
		for (const conversation of filteredConversations) {
			totalInputTokens += conversation.input_tokens;
			totalOutputTokens += conversation.output_tokens;
			totalAiCost += parseFloat(conversation.ai_cost || "0");
			totalAiCalls += conversation.message_count;
		}
	}

	if (includeAgents) {
		for (const agent of filteredAgents) {
			totalInputTokens += agent.input_tokens;
			totalOutputTokens += agent.output_tokens;
			totalAiCost += parseFloat(agent.ai_cost || "0");
			totalAiCalls += agent.run_count;
		}
	}

	const start = parseISO(startDate);
	const end = parseISO(endDate);
	const dayCount = Math.max(
		1,
		Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) +
			1,
	);

	const dailyCost = totalAiCost / dayCount;
	const dailyInputTokens = totalInputTokens / dayCount;
	const dailyOutputTokens = totalOutputTokens / dayCount;

	const trends: UsageTrend[] = [];
	const currentDate = new Date(start);
	let dayIndex = 0;

	while (currentDate <= end) {
		const isWeekend =
			currentDate.getDay() === 0 || currentDate.getDay() === 6;
		const baseMultiplier = isWeekend ? 0.5 : 1;
		const trendMultiplier = 1 + dayIndex * 0.003;
		const variance = 0.85 + Math.random() * 0.3;
		const dayFactor = baseMultiplier * trendMultiplier * variance;

		trends.push({
			date: format(currentDate, "yyyy-MM-dd"),
			ai_cost: (dailyCost * dayFactor).toFixed(2),
			input_tokens: Math.round(dailyInputTokens * dayFactor),
			output_tokens: Math.round(dailyOutputTokens * dayFactor),
		});

		currentDate.setDate(currentDate.getDate() + 1);
		dayIndex += 1;
	}

	const orgMetrics = new Map<
		string,
		{
			name: string;
			execution_count: number;
			conversation_count: number;
			input_tokens: number;
			output_tokens: number;
			ai_cost: number;
		}
	>();

	const applyOrgMetrics = (
		organizationId: string,
		organizationName: string,
		metrics: {
			execution_count?: number;
			conversation_count?: number;
			input_tokens: number;
			output_tokens: number;
			ai_cost: number;
		},
	) => {
		const existing = orgMetrics.get(organizationId);
		if (existing) {
			existing.execution_count += metrics.execution_count ?? 0;
			existing.conversation_count += metrics.conversation_count ?? 0;
			existing.input_tokens += metrics.input_tokens;
			existing.output_tokens += metrics.output_tokens;
			existing.ai_cost += metrics.ai_cost;
			return;
		}

		orgMetrics.set(organizationId, {
			name: organizationName,
			execution_count: metrics.execution_count ?? 0,
			conversation_count: metrics.conversation_count ?? 0,
			input_tokens: metrics.input_tokens,
			output_tokens: metrics.output_tokens,
			ai_cost: metrics.ai_cost,
		});
	};

	if (includeWorkflows) {
		for (const workflow of filteredWorkflows) {
			applyOrgMetrics(
				workflow.organization_id,
				orgs.find((org) => org.id === workflow.organization_id)?.name ??
					"Unknown",
				{
					execution_count: workflow.execution_count,
					input_tokens: workflow.input_tokens,
					output_tokens: workflow.output_tokens,
					ai_cost: parseFloat(workflow.ai_cost || "0"),
				},
			);
		}
	}

	if (includeConversations) {
		for (const conversation of filteredConversations) {
			applyOrgMetrics(
				conversation.organization_id,
				orgs.find((org) => org.id === conversation.organization_id)
					?.name ?? "Unknown",
				{
					conversation_count: 1,
					input_tokens: conversation.input_tokens,
					output_tokens: conversation.output_tokens,
					ai_cost: parseFloat(conversation.ai_cost || "0"),
				},
			);
		}
	}

	if (includeAgents) {
		for (const agent of filteredAgents) {
			applyOrgMetrics(
				agent.organization_id,
				orgs.find((org) => org.id === agent.organization_id)?.name ??
					"Unknown",
				{
					input_tokens: agent.input_tokens,
					output_tokens: agent.output_tokens,
					ai_cost: parseFloat(agent.ai_cost || "0"),
				},
			);
		}
	}

	const byOrganization = Array.from(orgMetrics.entries()).map(
		([organizationId, metrics]) => ({
			organization_id: organizationId,
			organization_name: metrics.name,
			execution_count: metrics.execution_count,
			conversation_count: metrics.conversation_count,
			input_tokens: metrics.input_tokens,
			output_tokens: metrics.output_tokens,
			ai_cost: metrics.ai_cost.toFixed(2),
		}),
	);

	return {
		summary: {
			total_ai_cost: totalAiCost.toFixed(2),
			total_input_tokens: totalInputTokens,
			total_output_tokens: totalOutputTokens,
			total_ai_calls: totalAiCalls,
			total_cpu_seconds: totalCpuSeconds,
			peak_memory_bytes: peakMemoryBytes,
		},
		trends,
		by_workflow: includeWorkflows ? filteredWorkflows : undefined,
		by_conversation: includeConversations
			? filteredConversations
			: undefined,
		by_agent: includeAgents ? filteredAgents : undefined,
		by_organization: byOrganization,
	};
}
