import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PROVIDERS, providerLabel } from "./providerOptions";
import type { AIProviderKind } from "@/services/aiModels";

export function ProviderCreateDialog({ providerCreateOpen, providerName, providerKind, providerEndpoint, providerKey, providerReady, setProviderName, changeProviderKind, setProviderEndpoint, setProviderKey, pending, error, onClose, onSubmit }: {
 providerCreateOpen: boolean;
 providerName: string;
 providerKind: AIProviderKind;
 providerEndpoint: string;
 providerKey: string;
 providerReady: boolean;
 setProviderName: (value: string) => void;
 changeProviderKind: (value: AIProviderKind) => void;
 setProviderEndpoint: (value: string) => void;
 setProviderKey: (value: string) => void;
 pending: boolean;
 error: Error | null;
 onClose: () => void;
 onSubmit: () => void;
}) {
 const dialogFocus = useDialogReturnFocus();

 return (
			<Dialog
				open={providerCreateOpen}
				onOpenChange={(open) => { if (!open && !pending) onClose(); }}
			>
				<DialogContent {...dialogFocus} className="sm:max-w-[560px]">
					<DialogHeader>
						<DialogTitle>Add Provider Connection</DialogTitle>
						<DialogDescription>
							Save a provider once, then reuse it across model
							profiles.
						</DialogDescription>
					</DialogHeader>
					<fieldset disabled={pending} className="grid min-w-0 gap-4 py-2">
						<div className="grid gap-4 sm:grid-cols-2">
							<div className="space-y-2">
								<Label htmlFor="ai-provider-kind">
									Provider
								</Label>
								<Select
								disabled={pending}
									value={providerKind}
									onValueChange={(value) =>
										changeProviderKind(
											value as AIProviderKind,
										)
									}
								>
									<SelectTrigger
										id="ai-provider-kind"
										className="h-auto min-h-11 w-full data-[size=default]:h-auto [&_[data-slot=select-value]]:whitespace-normal [&_[data-slot=select-value]]:[overflow-wrap:anywhere]"
									>
										<SelectValue />
									</SelectTrigger>
									<SelectContent>
										{PROVIDERS.map((provider) => (
											<SelectItem
												key={provider.value}
												value={provider.value}
											>
												{provider.label}
											</SelectItem>
										))}
									</SelectContent>
								</Select>
							</div>
							<div className="space-y-2">
								<Label htmlFor="ai-provider-name">
									Connection Name
								</Label>
								<Input
									id="ai-provider-name"
									value={providerName}
									onChange={(event) =>
										setProviderName(event.target.value)
									}
									placeholder="OpenAI Production"
								/>
							</div>
						</div>
						<div className="space-y-2">
							<Label htmlFor="ai-provider-endpoint">
								Endpoint
							</Label>
							<Input
								id="ai-provider-endpoint"
								value={providerEndpoint}
								onChange={(event) =>
									setProviderEndpoint(event.target.value)
								}
								placeholder="https://api.example.com/v1"
							/>
							<p className="text-xs text-muted-foreground">
								{providerKind === "openai_compatible"
									? "Required for OpenAI-Compatible providers."
									: `Prefilled with the standard ${providerLabel(providerKind)} endpoint.`}
							</p>
						</div>
						<div className="space-y-2">
							<Label htmlFor="ai-provider-key">API Key</Label>
							<Input
								id="ai-provider-key"
								type="password"
								value={providerKey}
								onChange={(event) =>
									setProviderKey(event.target.value)
								}
								placeholder="Paste a provider key"
							/>
						</div>
					</fieldset>
					{Boolean(error) && <p role="alert" className="text-sm text-destructive [overflow-wrap:anywhere]">{error instanceof Error ? error.message : "Could not save. Check the fields and try again."} Your entries are preserved.</p>}
					<DialogFooter>
						<Button className="min-h-11"
							variant="outline"
							disabled={pending}
							onClick={onClose}
						>
							Cancel
						</Button>
						<Button className="min-h-11"
							disabled={
								!providerReady ||
								pending
							}
							onClick={onSubmit}
						>
							{pending ? (
								<>
									<Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
									Verifying...
								</>
							) : (
								"Add Provider"
							)}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
 );
}
