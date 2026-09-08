import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PROVIDERS, providerOption, providerLabel } from "./providerOptions";
import type { AIProviderKind } from "@/services/aiModels";

export interface ProviderEditDraft {
 id: string;
 name: string;
 provider: AIProviderKind;
 endpoint: string;
 apiKey: string;
}

export function ProviderEditDialog({ providerEdit, pending, failed, onChange, onClose, onSave }: {
 providerEdit: ProviderEditDraft | null;
 pending: boolean;
 failed: boolean;
 onChange: (draft: ProviderEditDraft) => void;
 onClose: () => void;
 onSave: (draft: ProviderEditDraft) => void;
}) {
 const dialogFocus = useDialogReturnFocus();

 return (
			<Dialog
				open={providerEdit !== null}
				onOpenChange={(open) => { if (!open && !pending) onClose(); }}
			>
				<DialogContent {...dialogFocus}>
					<DialogHeader>
						<DialogTitle>Edit Provider Connection</DialogTitle>
						<DialogDescription>
							Update the connection once for every profile that
							uses it. Leave the key blank to keep the saved key.
						</DialogDescription>
					</DialogHeader>
					{providerEdit && (
						<fieldset disabled={pending} className="grid min-w-0 gap-4 py-2">
							<div className="space-y-2">
								<Label htmlFor="edit-provider-name">Name</Label>
								<Input
									id="edit-provider-name"
									value={providerEdit.name}
									onChange={(event) =>
										onChange({
											...providerEdit,
											name: event.target.value,
										})
									}
								/>
							</div>
							<div className="space-y-2">
								<Label htmlFor="edit-provider-kind">
									Provider
								</Label>
								<Select
									disabled={pending}
									value={providerEdit.provider}
									onValueChange={(provider) => {
										const nextKind =
											provider as AIProviderKind;
										const previousDefault = providerOption(
											providerEdit.provider,
										).endpoint;
										onChange({
											...providerEdit,
											provider: nextKind,
											endpoint:
												!providerEdit.endpoint ||
												providerEdit.endpoint ===
													previousDefault
													? providerOption(nextKind)
															.endpoint
													: providerEdit.endpoint,
										});
									}}
								>
									<SelectTrigger className="h-auto min-h-11 w-full data-[size=default]:h-auto [&_[data-slot=select-value]]:whitespace-normal [&_[data-slot=select-value]]:[overflow-wrap:anywhere]" id="edit-provider-kind">
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
								<Label htmlFor="edit-provider-endpoint">
									Endpoint
								</Label>
								<Input
									id="edit-provider-endpoint"
									value={providerEdit.endpoint}
									onChange={(event) =>
										onChange({
											...providerEdit,
											endpoint: event.target.value,
										})
									}
									placeholder="https://api.example.com/v1"
								/>
								<p className="text-xs text-muted-foreground">
									{providerEdit.provider ===
									"openai_compatible"
										? "Required for OpenAI-Compatible providers."
										: `Standard ${providerLabel(providerEdit.provider)} endpoint.`}
								</p>
							</div>
							<div className="space-y-2">
								<Label htmlFor="edit-provider-key">
									New API Key
								</Label>
								<Input
									id="edit-provider-key"
									type="password"
									value={providerEdit.apiKey}
									onChange={(event) =>
										onChange({
											...providerEdit,
											apiKey: event.target.value,
										})
									}
									placeholder="Leave blank to keep the saved key"
								/>
							</div>
						</fieldset>
					)}
					{failed && <p role="alert" className="text-sm text-destructive">Could not update this provider connection. Your entries are preserved. Check the fields and try again.</p>}
					<DialogFooter>
						<Button className="min-h-11"
							variant="outline"
							disabled={pending}
							onClick={() => onClose()}
						>
							Cancel
						</Button>
						<Button className="min-h-11"
							disabled={
								!providerEdit?.name.trim() ||
								pending
							}
							onClick={() =>
								providerEdit && !pending &&
								onSave(providerEdit)
							}
						>
							{pending ? (
								<>
									<Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
									Saving…
								</>
							) : (
								"Save Provider"
							)}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
 );
}
