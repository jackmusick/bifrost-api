import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Check, ChevronsUpDown, Loader2, AlertTriangle } from "lucide-react";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
	Form,
	FormControl,
	FormDescription,
	FormField,
	FormItem,
	FormLabel,
	FormMessage,
} from "@/components/ui/form";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import {
	Command,
	CommandEmpty,
	CommandGroup,
	CommandInput,
	CommandItem,
	CommandList,
} from "@/components/ui/command";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useSetConfig } from "@/hooks/useConfig";
import { useSecrets } from "@/hooks/useSecrets";
import type { components } from "@/lib/v1";

type Config = components["schemas"]["Config"];

const formSchema = z
	.object({
		key: z
			.string()
			.min(1, "Key is required")
			.regex(
				/^[a-zA-Z0-9_]+$/,
				"Key must be alphanumeric with underscores",
			),
		value: z.string().optional(),
		secretRef: z.string().optional(),
		type: z.enum(["string", "int", "bool", "json", "secret"]),
		description: z.string().optional(),
	})
	.refine(
		(data) => {
			// For secret type, require exactly one of value or secretRef
			if (data.type === "secret") {
				const hasValue = data.value && data.value.length > 0;
				const hasSecretRef =
					data.secretRef && data.secretRef.length > 0;
				return (
					(hasValue && !hasSecretRef) || (!hasValue && hasSecretRef)
				);
			}
			// For non-secret types, require value
			return data.value && data.value.length > 0;
		},
		{
			message:
				"For secret type, provide either value (to create/update) or secretRef (to reference existing)",
			path: ["value"],
		},
	);

type FormValues = z.infer<typeof formSchema>;

interface ConfigDialogProps {
	config?: Config | undefined;
	open: boolean;
	onClose: () => void;
}

export function ConfigDialog({ config, open, onClose }: ConfigDialogProps) {
	const setConfig = useSetConfig();
	const isEditing = !!config;
	const [comboboxOpen, setComboboxOpen] = useState(false);

	// For editing: default to "reference", for creating: default to "create"
	const [secretMode, setSecretMode] = useState<"create" | "reference">(
		isEditing ? "reference" : "create",
	);

	// Store the selected reference separately so we don't lose it when toggling
	const [selectedReference, setSelectedReference] = useState<string>("");

	// Track if user has entered a new secret value (for warning on update)
	const [hasEnteredNewValue, setHasEnteredNewValue] = useState(false);

	// State for update confirmation dialog
	const [showUpdateConfirmation, setShowUpdateConfirmation] = useState(false);
	const [pendingValues, setPendingValues] = useState<FormValues | null>(null);

	const form = useForm<FormValues>({
		resolver: zodResolver(formSchema),
		defaultValues: {
			key: "",
			value: "",
			secretRef: "",
			type: "string",
			description: "",
		},
	});

	// Watch the type field to conditionally render secret selector
	const selectedType = form.watch("type");

	// Fetch all secrets for the dropdown
	const { data: secretsData, isLoading: secretsLoading } = useSecrets();

	useEffect(() => {
		if (config) {
			// If editing a secret type, set to reference mode and populate secretRef
			if (config.type === "secret") {
				form.reset({
					key: config.key,
					value: "",
					secretRef: String(config.value ?? ""), // Existing secret reference
					type: config.type,
					description: config.description ?? "",
				});
				setSelectedReference(String(config.value ?? ""));
				setSecretMode("reference");
				setHasEnteredNewValue(false);
			} else {
				// Non-secret types
				form.reset({
					key: config.key,
					value: String(config.value ?? ""),
					secretRef: "",
					type: config.type,
					description: config.description ?? "",
				});
			}
		} else {
			form.reset({
				key: "",
				value: "",
				secretRef: "",
				type: "string",
				description: "",
			});
			setSecretMode("create");
			setSelectedReference("");
			setHasEnteredNewValue(false);
		}
	}, [config, form, open]);

	const onSubmit = async (values: FormValues) => {
		// Handle secret type specially
		if (values.type === "secret") {
			if (secretMode === "reference") {
				// Using existing reference - use the selected reference as value
				await setConfig.mutateAsync({
					key: values.key,
					value: selectedReference || "",
					type: values.type,
					description: values.description ?? null,
				});
			} else {
				// Creating/updating secret with value
				if (isEditing && hasEnteredNewValue) {
					// Show confirmation dialog instead of native confirm
					setPendingValues(values);
					setShowUpdateConfirmation(true);
					return;
				}
				await setConfig.mutateAsync({
					key: values.key,
					value: values.value ?? "",
					type: values.type,
					description: values.description ?? null,
				});
			}
		} else {
			// Non-secret types
			await setConfig.mutateAsync({
				key: values.key,
				value: values.value ?? "",
				type: values.type,
				description: values.description ?? null,
			});
		}
		onClose();
	};

	const handleConfirmUpdate = async () => {
		if (!pendingValues) return;

		await setConfig.mutateAsync({
			key: pendingValues.key,
			value: pendingValues.value ?? "",
			type: pendingValues.type,
			description: pendingValues.description ?? null,
		});

		setShowUpdateConfirmation(false);
		setPendingValues(null);
		onClose();
	};

	return (
		<>
			<Dialog open={open} onOpenChange={onClose}>
				<DialogContent className="sm:max-w-[600px]">
					<DialogHeader>
						<DialogTitle>
							{isEditing
								? "Edit Configuration"
								: "Add Configuration"}
						</DialogTitle>
						<DialogDescription>
							{isEditing
								? "Update the configuration value"
								: "Create a new configuration entry"}
						</DialogDescription>
					</DialogHeader>

					<Form {...form}>
						<form
							onSubmit={form.handleSubmit(onSubmit)}
							className="space-y-4"
						>
							<FormField
								control={form.control}
								name="key"
								render={({ field }) => (
									<FormItem>
										<FormLabel>Key</FormLabel>
										<FormControl>
											<Input
												placeholder="CONFIG_KEY_NAME"
												{...field}
												disabled={isEditing}
												className="font-mono"
											/>
										</FormControl>
										<FormDescription>
											Alphanumeric characters and
											underscores only
										</FormDescription>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="type"
								render={({ field }) => (
									<FormItem>
										<FormLabel>Type</FormLabel>
										<Select
											onValueChange={field.onChange}
											defaultValue={field.value}
										>
											<FormControl>
												<SelectTrigger>
													<SelectValue placeholder="Select type" />
												</SelectTrigger>
											</FormControl>
											<SelectContent>
												<SelectItem value="string">
													String
												</SelectItem>
												<SelectItem value="int">
													Integer
												</SelectItem>
												<SelectItem value="bool">
													Boolean
												</SelectItem>
												<SelectItem value="json">
													JSON
												</SelectItem>
												<SelectItem value="secret">
													Secret
												</SelectItem>
											</SelectContent>
										</Select>
										<FormDescription>
											{selectedType === "secret" &&
												"References a secret stored in Azure Key Vault"}
										</FormDescription>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="value"
								render={({ field }) => (
									<FormItem className="flex flex-col">
										<FormLabel>Value</FormLabel>
										{selectedType === "secret" ? (
											<>
												{/* Toggle group for create/update vs reference existing secret */}
												<ToggleGroup
													type="single"
													value={secretMode}
													onValueChange={(value) => {
														if (value) {
															setSecretMode(
																value as
																	| "create"
																	| "reference",
															);
															// When switching to reference mode, restore the saved reference
															if (
																value ===
																"reference"
															) {
																form.setValue(
																	"secretRef",
																	selectedReference,
																);
																form.setValue(
																	"value",
																	"",
																);
															} else {
																// When switching to create/update mode, clear the secretRef
																form.setValue(
																	"secretRef",
																	"",
																);
																form.setValue(
																	"value",
																	"",
																);
																setHasEnteredNewValue(
																	false,
																);
															}
														}
													}}
													className="justify-start mb-2"
												>
													<ToggleGroupItem
														value="create"
														aria-label="Create or update secret"
													>
														{isEditing
															? "Update Secret"
															: "Create New Secret"}
													</ToggleGroupItem>
													<ToggleGroupItem
														value="reference"
														aria-label="Reference existing secret"
													>
														Reference Existing
													</ToggleGroupItem>
												</ToggleGroup>

												{secretMode === "create" ? (
													<>
														<FormControl>
															<Input
																type="password"
																placeholder="Enter secret value"
																className="font-mono"
																{...field}
																onChange={(
																	e,
																) => {
																	field.onChange(
																		e,
																	);
																	// Track that user has entered a new value
																	if (
																		isEditing
																	) {
																		setHasEnteredNewValue(
																			e
																				.target
																				.value
																				.length >
																				0,
																		);
																	}
																}}
															/>
														</FormControl>
														<FormDescription>
															{isEditing
																? "Enter a new value to update the secret (creates a new version in Key Vault)"
																: "Secret will be automatically created in Key Vault with a unique name"}
														</FormDescription>
													</>
												) : (
													<>
														<Popover
															open={comboboxOpen}
															onOpenChange={
																setComboboxOpen
															}
														>
															<FormControl>
																<PopoverTrigger
																	asChild
																>
																	<Button
																		variant="outline"
																		role="combobox"
																		aria-expanded={
																			comboboxOpen
																		}
																		className={cn(
																			"w-full justify-between font-mono",
																			!selectedReference &&
																				"text-muted-foreground",
																		)}
																	>
																		{selectedReference ||
																			"Select a secret..."}
																		<ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
																	</Button>
																</PopoverTrigger>
															</FormControl>
															<PopoverContent
																className="p-0"
																align="start"
																style={{
																	width: "var(--radix-popover-trigger-width)",
																}}
															>
																<Command>
																	<CommandInput placeholder="Search secrets..." />
																	<CommandList>
																		<CommandEmpty>
																			{secretsLoading
																				? "Loading secrets..."
																				: "No secrets found."}
																		</CommandEmpty>
																		<CommandGroup>
																			{Array.isArray(secretsData?.secrets) &&
																				secretsData.secrets.map(
																					(
																						secretName: string,
																					) => (
																						<CommandItem
																							key={
																								secretName
																							}
																							value={
																								secretName
																							}
																							onSelect={() => {
																								form.setValue(
																									"secretRef",
																									secretName,
																								);
																								setSelectedReference(
																									secretName,
																								); // Save the reference
																								setComboboxOpen(
																									false,
																								);
																							}}
																							className="font-mono"
																						>
																							<Check
																								className={cn(
																									"mr-2 h-4 w-4",
																									selectedReference ===
																										secretName
																										? "opacity-100"
																										: "opacity-0",
																								)}
																							/>
																							{
																								secretName
																							}
																						</CommandItem>
																					),
																				)}
																		</CommandGroup>
																	</CommandList>
																</Command>
															</PopoverContent>
														</Popover>
														<FormDescription>
															Select a secret name
															from Azure Key
															Vault. Scope is
															determined by this
															config entry.
														</FormDescription>
													</>
												)}
											</>
										) : (
											<>
												<FormControl>
													<Textarea
														placeholder="Configuration value"
														className="font-mono"
														{...field}
													/>
												</FormControl>
												<FormDescription>
													Enter the configuration
													value
												</FormDescription>
											</>
										)}
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="description"
								render={({ field }) => (
									<FormItem>
										<FormLabel>
											Description (Optional)
										</FormLabel>
										<FormControl>
											<Input
												placeholder="What is this config for?"
												{...field}
											/>
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<DialogFooter>
								<Button
									type="button"
									variant="outline"
									onClick={onClose}
								>
									Cancel
								</Button>
								<Button
									type="submit"
									disabled={
										setConfig.isPending ||
										!form.formState.isValid
									}
								>
									{setConfig.isPending && (
										<Loader2 className="mr-2 h-4 w-4 animate-spin" />
									)}
									{setConfig.isPending
										? "Saving..."
										: isEditing
											? "Update"
											: "Create"}
								</Button>
							</DialogFooter>
						</form>
					</Form>
				</DialogContent>
			</Dialog>

			{/* Confirmation dialog for updating secret */}
			<AlertDialog
				open={showUpdateConfirmation}
				onOpenChange={setShowUpdateConfirmation}
			>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle className="flex items-center gap-2">
							<AlertTriangle className="h-5 w-5 text-yellow-500" />
							Update Secret Value
						</AlertDialogTitle>
						<AlertDialogDescription className="space-y-3">
							<p>
								You are about to update the secret value for{" "}
								<strong className="text-foreground">
									{pendingValues?.key}
								</strong>
								.
							</p>
							<p>
								This will create a new version in Azure Key
								Vault. The previous version will still be
								accessible but this config will reference the
								new version.
							</p>
							<p className="text-sm text-muted-foreground">
								Are you sure you want to continue?
							</p>
						</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel
							onClick={() => {
								setShowUpdateConfirmation(false);
								setPendingValues(null);
							}}
						>
							Cancel
						</AlertDialogCancel>
						<AlertDialogAction onClick={handleConfirmUpdate}>
							Yes, Update Secret
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</>
	);
}
