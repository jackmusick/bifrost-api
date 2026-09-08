import { GeneratedSDKSummary } from "./GeneratedSDKSummary";
import { useState } from "react";
import { Loader2, Code, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import {
	useGenerateSDK,
	useUpdateIntegrationConfig,
} from "@/services/integrations";
import type { components } from "@/lib/v1";

type AuthType = "bearer" | "api_key" | "basic" | "oauth";

type GenerateSDKResponse = components["schemas"]["GenerateSDKResponse"];

interface GenerateSDKDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	integrationId: string;
	integrationName: string;
	hasOAuth: boolean;
}

export function GenerateSDKDialog({
	open,
	onOpenChange,
	integrationId,
	integrationName,
	hasOAuth,
}: GenerateSDKDialogProps) {
	const [copyMessage, setCopyMessage] = useState<string | null>(null);
	const [specUrl, setSpecUrl] = useState("");
	const [authType, setAuthType] = useState<AuthType>("bearer");
	const [moduleName, setModuleName] = useState("");
	const [result, setResult] = useState<GenerateSDKResponse | null>(null);
	const [generatedSDK, setGeneratedSDK] =
		useState<GenerateSDKResponse | null>(null);
	const [generationError, setGenerationError] = useState<string | null>(null);
	const [isSubmitting, setIsSubmitting] = useState(false);

	// React Query mutations
	const generateSDKMutation = useGenerateSDK();
	const updateConfigMutation = useUpdateIntegrationConfig();

	const isGenerating =
		isSubmitting ||
		generateSDKMutation.isPending ||
		updateConfigMutation.isPending;

	// Auth-specific fields
	const [baseUrl, setBaseUrl] = useState("");
	const [token, setToken] = useState("");
	const [headerName, setHeaderName] = useState("x-api-key");
	const [apiKey, setApiKey] = useState("");
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");

	const validateAuthFields = (): string | null => {
		if (!baseUrl.trim()) {
			return "Base URL is required";
		}

		switch (authType) {
			case "bearer":
				if (!token.trim()) return "Token is required";
				break;
			case "api_key":
				if (!headerName.trim()) return "Header name is required";
				if (!apiKey.trim()) return "API key is required";
				break;
			case "basic":
				if (!username.trim()) return "Username is required";
				if (!password.trim()) return "Password is required";
				break;
			case "oauth":
				// OAuth uses existing provider, no extra fields needed
				break;
		}
		return null;
	};

	const buildConfigPayload = (): Record<string, string> => {
		const config: Record<string, string> = {
			base_url: baseUrl.trim(),
		};

		switch (authType) {
			case "bearer":
				config.token = token.trim();
				break;
			case "api_key":
				config.header_name = headerName.trim();
				config.api_key = apiKey.trim();
				break;
			case "basic":
				config.username = username.trim();
				config.password = password.trim();
				break;
		}

		return config;
	};

	const handleGenerate = async (e: React.FormEvent) => {
		e.preventDefault();
		if (isGenerating) return;
		if (!specUrl.trim()) {
			setGenerationError("Please enter an OpenAPI spec URL");
			return;
		}

		const validationError = validateAuthFields();
		if (validationError) {
			setGenerationError(validationError);
			return;
		}

		setGenerationError(null);
		setIsSubmitting(true);
		let sdkResult = generatedSDK;
		try {
			// Generate SDK first - this creates the config schema (secret types, etc.)
			sdkResult =
				generatedSDK ??
				(await generateSDKMutation.mutateAsync({
					params: { path: { integration_id: integrationId } },
					body: {
						spec_url: specUrl.trim(),
						auth_type: authType,
						module_name: moduleName.trim() || undefined,
					},
				}));

			setGeneratedSDK(sdkResult);

			// Save config AFTER schema exists so _save_config correctly encrypts secrets
			await updateConfigMutation.mutateAsync({
				params: { path: { integration_id: integrationId } },
				body: { config: buildConfigPayload() },
			});

			setResult(sdkResult);
		} catch {
			setGenerationError(
				sdkResult
					? "SDK generated, but configuration could not be saved. Review the settings and retry saving configuration."
					: "Unable to generate the SDK. Check the specification URL and try again.",
			);
		} finally {
			setIsSubmitting(false);
		}
	};

	const handleCopyUsage = async () => {
		if (result?.usage_example) {
			try {
				await navigator.clipboard.writeText(result.usage_example);
				setCopyMessage("Usage example copied to clipboard.");
			} catch {
				setCopyMessage(
					"Unable to copy. Select and copy the usage example manually.",
				);
			}
		}
	};

	const handleClose = () => {
		if (isGenerating) return;
		setCopyMessage(null);
		setGeneratedSDK(null);
		setGenerationError(null);
		// Reset state when closing
		setSpecUrl("");
		setAuthType("bearer");
		setModuleName("");
		setResult(null);
		setBaseUrl("");
		setToken("");
		setHeaderName("x-api-key");
		setApiKey("");
		setUsername("");
		setPassword("");
		onOpenChange(false);
	};

	const renderAuthFields = () => {
		return (
			<>
				{/* Base URL - always shown */}
				<div className="space-y-2">
					<Label htmlFor="base-url">
						Base URL <span className="text-destructive">*</span>
					</Label>
					<Input
						className="min-h-11"
						disabled={isGenerating}
						id="base-url"
						placeholder="https://api.example.com"
						value={baseUrl}
						onChange={(e) => setBaseUrl(e.target.value)}
					/>
				</div>

				{/* Bearer Token fields */}
				{authType === "bearer" && (
					<div className="space-y-2">
						<Label htmlFor="token">
							Token <span className="text-destructive">*</span>
						</Label>
						<Input
							className="min-h-11"
							disabled={isGenerating}
							id="token"
							type="password"
							autoComplete="new-password"
							placeholder="Enter your API token"
							value={token}
							onChange={(e) => setToken(e.target.value)}
						/>
					</div>
				)}

				{/* API Key fields */}
				{authType === "api_key" && (
					<>
						<div className="space-y-2">
							<Label htmlFor="header-name">
								Header Name{" "}
								<span className="text-destructive">*</span>
							</Label>
							<Input
								className="min-h-11"
								disabled={isGenerating}
								id="header-name"
								placeholder="x-api-key"
								value={headerName}
								onChange={(e) => setHeaderName(e.target.value)}
							/>
							<p className="text-xs text-muted-foreground">
								The HTTP header name for authentication (e.g.,
								x-api-key, X-Auth-Token)
							</p>
						</div>
						<div className="space-y-2">
							<Label htmlFor="api-key">
								API Key{" "}
								<span className="text-destructive">*</span>
							</Label>
							<Input
								className="min-h-11"
								disabled={isGenerating}
								id="api-key"
								type="password"
								autoComplete="new-password"
								placeholder="Enter your API key"
								value={apiKey}
								onChange={(e) => setApiKey(e.target.value)}
							/>
						</div>
					</>
				)}

				{/* Basic Auth fields */}
				{authType === "basic" && (
					<>
						<div className="space-y-2">
							<Label htmlFor="username">
								Username{" "}
								<span className="text-destructive">*</span>
							</Label>
							<Input
								className="min-h-11"
								disabled={isGenerating}
								id="username"
								placeholder="Enter username"
								value={username}
								onChange={(e) => setUsername(e.target.value)}
							/>
						</div>
						<div className="space-y-2">
							<Label htmlFor="password">
								Password{" "}
								<span className="text-destructive">*</span>
							</Label>
							<Input
								className="min-h-11"
								disabled={isGenerating}
								id="password"
								type="password"
								autoComplete="new-password"
								placeholder="Enter password"
								value={password}
								onChange={(e) => setPassword(e.target.value)}
							/>
						</div>
					</>
				)}

				{/* OAuth - no extra fields, just info */}
				{authType === "oauth" && (
					<div className="text-sm text-muted-foreground rounded-md bg-muted/50 p-3 ring-1 ring-foreground/5">
						OAuth authentication will use the integration's
						configured OAuth provider. Make sure you've connected
						the OAuth flow before using the SDK.
					</div>
				)}
			</>
		);
	};

	const getConfigInfoMessage = () => {
		switch (authType) {
			case "bearer":
				return "Will save base_url and token to integration config";
			case "api_key":
				return "Will save base_url, header_name, and api_key to integration config";
			case "basic":
				return "Will save base_url, username, and password to integration config";
			case "oauth":
				return "Will use the existing OAuth connection for authentication";
		}
	};

	return (
		<Dialog open={open} onOpenChange={handleClose}>
			<DialogContent className="max-w-xl">
				{result ? (
					// Success state
					<>
						<DialogHeader>
							<DialogTitle className="flex items-start gap-2 [overflow-wrap:anywhere]">
								<CheckCircle2 className="h-5 w-5 shrink-0 text-[var(--bf-success)]" />
								SDK Generated Successfully
							</DialogTitle>
							<DialogDescription>
								Your SDK is ready to use in workflows
							</DialogDescription>
						</DialogHeader>

						<div className="space-y-4 py-4">
							<GeneratedSDKSummary
								result={result}
								onCopy={handleCopyUsage}
								copyMessage={copyMessage}
							/>
							<div className="text-sm text-muted-foreground bg-[var(--bf-success-soft)] text-[var(--bf-success)] p-3 rounded-md">
								<p>
									<strong>Configuration saved!</strong> The
									authentication settings have been saved to
									the integration config. The SDK will
									automatically use these credentials.
								</p>
							</div>
						</div>

						<DialogFooter>
							<Button className="min-h-11" onClick={handleClose}>
								Done
							</Button>
						</DialogFooter>
					</>
				) : (
					// Form state
					<form onSubmit={handleGenerate}>
						<DialogHeader>
							<DialogTitle className="flex items-start gap-2 [overflow-wrap:anywhere]">
								<Code className="h-5 w-5 shrink-0" />
								Generate SDK for {integrationName}
							</DialogTitle>
							<DialogDescription>
								Generate a Python SDK from an OpenAPI
								specification. The SDK will automatically use
								this integration's configuration for
								authentication.
							</DialogDescription>
						</DialogHeader>

						<div className="space-y-4 py-4">
							<div className="space-y-2">
								<Label htmlFor="spec-url">
									OpenAPI Spec URL{" "}
									<span className="text-destructive">*</span>
								</Label>
								<Input
									className="min-h-11"
									disabled={isGenerating || !!generatedSDK}
									id="spec-url"
									placeholder="https://api.example.com/openapi.json"
									value={specUrl}
									onChange={(e) => setSpecUrl(e.target.value)}
								/>
								<p className="text-xs text-muted-foreground">
									URL to an OpenAPI 3.0 specification (JSON or
									YAML)
								</p>
							</div>

							<div className="space-y-2">
								<Label htmlFor="auth-type">
									Authentication Type{" "}
									<span className="text-destructive">*</span>
								</Label>
								<Select
									disabled={isGenerating || !!generatedSDK}
									value={authType}
									onValueChange={(v) =>
										setAuthType(v as AuthType)
									}
								>
									<SelectTrigger
										id="auth-type"
										className="min-h-11"
									>
										<SelectValue />
									</SelectTrigger>
									<SelectContent>
										<SelectItem value="bearer">
											Bearer Token
										</SelectItem>
										<SelectItem value="api_key">
											API Key (custom header)
										</SelectItem>
										<SelectItem value="basic">
											Basic Auth
										</SelectItem>
										{hasOAuth && (
											<SelectItem value="oauth">
												OAuth (use configured provider)
											</SelectItem>
										)}
									</SelectContent>
								</Select>
							</div>

							{/* Dynamic auth fields based on selected type */}
							{renderAuthFields()}

							<div className="space-y-2">
								<Label htmlFor="module-name">
									Module Name{" "}
									<span className="text-muted-foreground">
										(optional)
									</span>
								</Label>
								<Input
									className="min-h-11"
									disabled={isGenerating || !!generatedSDK}
									id="module-name"
									placeholder="example_api"
									value={moduleName}
									onChange={(e) =>
										setModuleName(e.target.value)
									}
									pattern="^[a-z][a-z0-9_]*$"
								/>
								<p className="text-xs text-muted-foreground">
									Lowercase with underscores. Defaults to the
									API title from the spec.
								</p>
							</div>

							{/* Info message about what will be saved */}
							<div className="text-sm text-muted-foreground bg-muted text-muted-foreground p-3 rounded-md flex items-start gap-2">
								<span className="mt-0.5">ℹ️</span>
								<span>{getConfigInfoMessage()}</span>
							</div>
						</div>

						{generationError && (
							<p
								role="alert"
								className="mb-4 text-sm text-destructive [overflow-wrap:anywhere]"
							>
								{generationError}
							</p>
						)}
						<DialogFooter>
							<Button
								className="min-h-11"
								type="button"
								variant="outline"
								onClick={handleClose}
								disabled={isGenerating}
							>
								Cancel
							</Button>
							<Button
								className="min-h-11"
								type="submit"
								disabled={isGenerating || !specUrl.trim()}
							>
								{isGenerating ? (
									<>
										<Loader2 className="h-4 w-4 mr-2 animate-spin motion-reduce:animate-none" />
										{generatedSDK
											? "Saving configuration…"
											: "Generating..."}
									</>
								) : (
									<>
										<Code className="h-4 w-4 mr-2" />
										{generatedSDK
											? "Retry configuration save"
											: "Generate SDK"}
									</>
								)}
							</Button>
						</DialogFooter>
					</form>
				)}
			</DialogContent>
		</Dialog>
	);
}
