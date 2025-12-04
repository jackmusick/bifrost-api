import { useState } from "react";
import { Copy, Check, Webhook, RefreshCw, AlertTriangle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useWorkflowKeys, useCreateWorkflowKey } from "@/hooks/useWorkflowKeys";
import type { components } from "@/lib/v1";
type Workflow = components["schemas"]["WorkflowMetadata"];

interface HttpTriggerDialogProps {
	workflow: Workflow;
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

export function HttpTriggerDialog({
	workflow,
	open,
	onOpenChange,
}: HttpTriggerDialogProps) {
	const [copiedCurl, setCopiedCurl] = useState(false);
	const [newlyGeneratedKey, setNewlyGeneratedKey] = useState<string | null>(
		null,
	);
	const navigate = useNavigate();

	// Get base URL from current browser location
	const baseUrl = `${window.location.protocol}//${window.location.host}`;
	const directUrl = `${baseUrl}/api/endpoints/${workflow.name}`;

	// Query for existing workflow-specific key
	const { data: existingKeys, refetch: refetchKeys } = useWorkflowKeys({
		workflowId: workflow.name,
		includeRevoked: false,
	});
	const createKeyMutation = useCreateWorkflowKey();

	// Get the workflow's key (only one per workflow)
	const workflowKey = existingKeys?.[0];
	const displayKey = newlyGeneratedKey || workflowKey?.masked_key || "";
	const hasKey = !!workflowKey || !!newlyGeneratedKey;

	// Handle key generation
	const handleGenerateKey = async () => {
		try {
			const result = await createKeyMutation.mutateAsync({
				workflow_name: workflow.name,
				disable_global_key: false,
			});
			if (result.raw_key) {
				setNewlyGeneratedKey(result.raw_key);
				refetchKeys();
			}
		} catch {
			// Silently handle error
		}
	};

	const copyToClipboard = async (
		text: string,
		setCopied: (value: boolean) => void,
	) => {
		try {
			await navigator.clipboard.writeText(text);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch {
			// Silently handle clipboard error
		}
	};

	// Check if this is a public endpoint (webhook)
	const isPublicEndpoint = workflow.public_endpoint ?? false;

	// Example parameters
	const exampleParams =
		workflow.parameters?.reduce(
			(acc, param) => ({
				...acc,
				[param.name ?? "param"]:
					param.type === "string"
						? "<string>"
						: param.type === "int"
							? 0
							: param.type === "bool"
								? false
								: null,
			}),
			{} as Record<string, unknown>,
		) ?? {};

	// cURL example - skip auth header for public endpoints
	const apiKeyValue = displayKey || "YOUR_API_KEY";
	const curlExample = isPublicEndpoint
		? `curl -X POST "${directUrl}" \\
  -H "Content-Type: application/json" \\
  -d '${JSON.stringify(exampleParams, null, 2)}'`
		: `curl -X POST "${directUrl}" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${apiKeyValue}" \\
  -d '${JSON.stringify(exampleParams, null, 2)}'`;

	const handleManageKeys = () => {
		onOpenChange(false);
		navigate("/settings/workflow-keys");
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-2xl">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<Webhook className="h-5 w-5" />
						HTTP Endpoint Configuration
						{isPublicEndpoint && (
							<span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-destructive/10 text-destructive rounded-md border border-destructive/20">
								<AlertTriangle className="h-3 w-3" />
								Public
							</span>
						)}
					</DialogTitle>
					<DialogDescription>
						Call{" "}
						<span className="font-mono font-semibold">
							{workflow.name}
						</span>{" "}
						via HTTP endpoint
						{isPublicEndpoint && (
							<span className="block mt-1 text-destructive">
								This is a public webhook endpoint - no
								authentication required
							</span>
						)}
					</DialogDescription>
				</DialogHeader>

				<div className="space-y-6">
					{/* Parameters List */}
					{workflow.parameters && workflow.parameters.length > 0 && (
						<div className="space-y-2">
							<label className="text-sm font-medium">
								Parameters
							</label>
							<div className="bg-muted rounded-md p-4 space-y-2">
								{workflow.parameters.map((param) => (
									<div
										key={param.name}
										className="flex items-start gap-2 text-sm"
									>
										<code className="font-mono text-xs bg-background px-2 py-1 rounded">
											{param.name}
											{param.required && (
												<span className="text-destructive">
													*
												</span>
											)}
										</code>
										<span className="text-muted-foreground">
											({param.type})
											{param.description &&
												` - ${param.description}`}
										</span>
									</div>
								))}
							</div>
							<p className="text-xs text-muted-foreground">
								<span className="text-destructive">*</span>{" "}
								Required parameters
							</p>
						</div>
					)}

					{/* API Key Management - Hidden for public endpoints */}
					{!isPublicEndpoint && (
						<div className="space-y-2">
							<label className="text-sm font-medium">
								Workflow API Key
							</label>
							{hasKey ? (
								<div className="flex items-center gap-2">
									<Input
										type="text"
										value={displayKey}
										readOnly
										className="font-mono text-xs flex-1"
									/>
									<Button
										variant="outline"
										size="sm"
										onClick={handleGenerateKey}
										disabled={createKeyMutation.isPending}
										title="Regenerate API key"
									>
										{createKeyMutation.isPending ? (
											<RefreshCw className="h-4 w-4 animate-spin" />
										) : (
											<RefreshCw className="h-4 w-4" />
										)}
									</Button>
								</div>
							) : (
								<div className="flex items-center gap-2">
									<p className="text-sm text-muted-foreground flex-1">
										No API key configured for this workflow
									</p>
									<Button
										variant="default"
										size="sm"
										onClick={handleGenerateKey}
										disabled={createKeyMutation.isPending}
									>
										{createKeyMutation.isPending ? (
											<>
												<RefreshCw className="mr-2 h-4 w-4 animate-spin" />
												Generating...
											</>
										) : (
											<>
												<RefreshCw className="mr-2 h-4 w-4" />
												Generate Key
											</>
										)}
									</Button>
								</div>
							)}
							<p className="text-xs text-muted-foreground">
								{hasKey
									? "This key is permanent and specific to this workflow. Click refresh to regenerate."
									: "Generate a workflow-specific API key for authenticating HTTP requests."}
							</p>
						</div>
					)}

					{/* cURL Example */}
					<div className="space-y-2">
						<label className="text-sm font-medium">
							Example Request
						</label>
						<div className="relative">
							<pre className="p-4 bg-muted rounded-md text-xs overflow-x-auto">
								<code>{curlExample}</code>
							</pre>
							<Button
								variant="ghost"
								size="sm"
								className="absolute top-2 right-2"
								onClick={() =>
									copyToClipboard(curlExample, setCopiedCurl)
								}
							>
								{copiedCurl ? (
									<Check className="h-3 w-3" />
								) : (
									<Copy className="h-3 w-3" />
								)}
							</Button>
						</div>
						{!hasKey && !isPublicEndpoint && (
							<p className="text-xs text-muted-foreground">
								Generate a workflow API key above to
								authenticate requests
							</p>
						)}
						{isPublicEndpoint && (
							<p className="text-xs text-muted-foreground">
								This is a public endpoint - no authentication
								required
							</p>
						)}
					</div>

					{/* Manage API Keys Button */}
					<div className="flex justify-center pt-2">
						<Button onClick={handleManageKeys} variant="outline">
							Manage API Keys
						</Button>
					</div>
				</div>
			</DialogContent>
		</Dialog>
	);
}
