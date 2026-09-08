import {
	useCallback,
	useEffect,
	useLayoutEffect,
	useRef,
	useState,
} from "react";
import {
	CircleHelp,
	CheckCircle2,
	FileText,
	Image,
	Loader2,
	ShieldCheck,
	Wrench,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from "@/components/ui/tooltip";
import { authFetch } from "@/lib/api-client";
import type { components } from "@/lib/v1";
import { cn } from "@/lib/utils";

export type ModelCapabilities = components["schemas"]["ModelCapabilities"];

type CapabilityKey = "image_input" | "pdf_input" | "tool_calling";

const UNKNOWN: ModelCapabilities = {
	image_input: false,
	pdf_input: false,
	tool_calling: false,
	source: "unknown",
	fingerprint: "",
};

const CAPABILITIES = [
	{
		key: "image_input" as const,
		label: "Image Input",
		icon: Image,
	},
	{
		key: "pdf_input" as const,
		label: "PDF Input",
		icon: FileText,
	},
	{
		key: "tool_calling" as const,
		label: "Tool Calling",
		icon: Wrench,
	},
];

function sourceLabel(source: ModelCapabilities["source"]): string {
	return {
		openrouter: "OpenRouter",
		verified: "Verified",
		manual: "Manual",
		unknown: "Not Verified",
	}[source];
}

export function ModelCapabilityEditor({
	provider,
	model,
	endpoint,
	apiKey,
	value,
	onChange,
}: {
	provider: "openai" | "anthropic" | "google";
	model: string;
	endpoint: string;
	apiKey?: string;
	value: ModelCapabilities | null;
	onChange: (value: ModelCapabilities) => void;
}) {
	const [pending, setPending] = useState<{
		kind: "detect" | "verify";
		provider: string;
		model: string;
		endpoint: string;
		apiKey?: string;
	} | null>(null);
	const pendingForCurrentInput =
		pending?.provider === provider &&
		pending?.model === model &&
		pending?.endpoint === endpoint &&
		pending?.apiKey === apiKey;
	const detecting = pendingForCurrentInput && pending?.kind === "detect";
	const verifying = pendingForCurrentInput && pending?.kind === "verify";
	const mountedRef = useRef(false);
	const requestVersion = useRef(0);
	const currentRequest = useRef<{
		kind: "detect" | "verify";
		id: number;
	} | null>(null);
	const previousModel = useRef(model);
	const capabilities = value ?? UNKNOWN;
	const verified = capabilities.source !== "unknown";
	const SourceIcon = verified ? CheckCircle2 : CircleHelp;

	const invalidateRequests = useCallback(() => {
		requestVersion.current += 1;
		currentRequest.current = null;
	}, []);

	useLayoutEffect(() => {
		mountedRef.current = true;
		return () => {
			mountedRef.current = false;
			requestVersion.current += 1;
			currentRequest.current = null;
		};
	}, []);

	useLayoutEffect(() => {
		invalidateRequests();
	}, [provider, model, endpoint, apiKey, invalidateRequests]);

	const beginRequest = (kind: "detect" | "verify") => {
		if (
			!mountedRef.current ||
			!model.trim() ||
			currentRequest.current?.kind === kind
		)
			return null;
		const id = ++requestVersion.current;
		currentRequest.current = { kind, id };
		setPending({ kind, provider, model, endpoint, apiKey });
		return id;
	};

	const isCurrentRequest = (id: number) =>
		mountedRef.current && currentRequest.current?.id === id;

	const detect = async (announce = false) => {
		const requestId = beginRequest("detect");
		if (requestId === null) return;
		try {
			const response = await authFetch(
				"/api/admin/llm/model-capabilities",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						provider,
						model,
						endpoint: endpoint || null,
					}),
				},
			);
			if (!response.ok) throw new Error("Capability lookup failed");
			const result = (await response.json()) as {
				capabilities: ModelCapabilities;
				message: string;
			};
			if (!isCurrentRequest(requestId)) {
				return;
			}
			onChange(result.capabilities);
			if (announce) {
				toast.success("Capabilities Updated", {
					description: result.message,
				});
			}
		} catch {
			if (!isCurrentRequest(requestId)) {
				return;
			}
			toast.error("Capability Lookup Failed", {
				description:
					"Verify with the provider or set each capability manually.",
			});
		} finally {
			if (isCurrentRequest(requestId)) {
				invalidateRequests();
				setPending(null);
			}
		}
	};

	const verify = async () => {
		const requestId = beginRequest("verify");
		if (requestId === null) return;
		try {
			const response = await authFetch(
				"/api/admin/llm/model-capabilities/verify",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						provider,
						model,
						endpoint: endpoint || null,
						api_key: apiKey || null,
					}),
				},
			);
			const body = (await response.json().catch(() => ({}))) as {
				capabilities?: ModelCapabilities;
				message?: string;
				detail?: string;
			};
			if (!isCurrentRequest(requestId)) {
				return;
			}
			if (!response.ok || !body.capabilities) {
				throw new Error(
					body.detail || "Capability verification failed",
				);
			}
			onChange(body.capabilities);
			toast.success("Capabilities Verified", {
				description: body.message || "Provider verification completed.",
			});
		} catch (error) {
			if (!isCurrentRequest(requestId)) {
				return;
			}
			toast.error("Capability Verification Failed", {
				description:
					error instanceof Error
						? error.message
						: "Confirm the endpoint, key, and model, then retry.",
			});
		} finally {
			if (isCurrentRequest(requestId)) {
				invalidateRequests();
				setPending(null);
			}
		}
	};

	useEffect(() => {
		if (previousModel.current === model) return;
		previousModel.current = model;
		if (!model.trim()) return;
		const scheduledVersion = requestVersion.current;
		const timer = window.setTimeout(() => {
			if (requestVersion.current === scheduledVersion) void detect();
		}, 450);
		return () => window.clearTimeout(timer);
		// Detection deliberately follows model selection; callback identity is not an input.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [model, provider, endpoint, apiKey]);

	const toggle = (key: CapabilityKey) => {
		invalidateRequests();
		setPending(null);
		onChange({
			...capabilities,
			[key]: !capabilities[key],
			source: "manual",
		});
	};

	return (
		<TooltipProvider delayDuration={150}>
			<div className="flex min-w-0 flex-wrap items-center gap-2 text-sm">
				{CAPABILITIES.map((item) => {
					const Icon = item.icon;
					const unknown = capabilities.source === "unknown";
					const supported = capabilities[item.key];
					const state = unknown
						? "Not Verified"
						: supported
							? "Supported"
							: "Not Supported";
					return (
						<Tooltip key={item.key}>
							<TooltipTrigger asChild>
								<button
									type="button"
									onClick={() => toggle(item.key)}
									aria-label={`${item.label}: ${state}`}
									className={cn(
										"inline-flex min-h-11 items-center gap-2 px-3 rounded-[var(--bf-radius-control)] outline-none transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none",
										unknown && "text-[var(--bf-warning)]",
										supported &&
											!unknown &&
											"text-[var(--bf-success)]",
										!supported &&
											!unknown &&
											"text-[var(--bf-danger)]",
									)}
								>
									<Icon className="size-4 shrink-0" />
									<span>{item.label}</span>
								</button>
							</TooltipTrigger>
							<TooltipContent>
								<p className="font-medium">{item.label}</p>
								<p>
									{state} · {sourceLabel(capabilities.source)}
								</p>
								<p>Click to change manually.</p>
							</TooltipContent>
						</Tooltip>
					);
				})}

				<div className="flex flex-wrap items-center gap-2 sm:ml-auto">
					{capabilities.source === "unknown" && (
						<Tooltip>
							<TooltipTrigger asChild>
								<Button
									type="button"
									variant="ghost"
									size="icon"
									className="size-11 text-[var(--bf-info)]"
									onClick={() => void verify()}
									disabled={!model.trim() || verifying}
									aria-label="Verify With Provider"
								>
									{verifying ? (
										<Loader2 className="h-3 w-3 motion-safe:animate-spin" />
									) : (
										<ShieldCheck className="h-3 w-3" />
									)}
								</Button>
							</TooltipTrigger>
							<TooltipContent>
								Verify With Provider
							</TooltipContent>
						</Tooltip>
					)}
					<Tooltip>
						<TooltipTrigger asChild>
							<button
								type="button"
								className="flex min-h-11 items-center gap-2 rounded-[var(--bf-radius-control)] px-3 text-sm font-normal text-muted-foreground outline-none transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none"
								onClick={() => void detect(true)}
								disabled={!model.trim() || detecting}
								aria-label="Refresh Model Capabilities"
							>
								<span>{sourceLabel(capabilities.source)}</span>
								{detecting ? (
									<Loader2 className="h-3 w-3 motion-safe:animate-spin" />
								) : (
									<SourceIcon
										className={cn(
											"h-3 w-3",
											verified
												? "text-[var(--bf-success)]"
												: "text-[var(--bf-warning)]",
										)}
										aria-hidden="true"
									/>
								)}
							</button>
						</TooltipTrigger>
						<TooltipContent>
							Refresh Model Capabilities
						</TooltipContent>
					</Tooltip>
				</div>
			</div>
		</TooltipProvider>
	);
}
