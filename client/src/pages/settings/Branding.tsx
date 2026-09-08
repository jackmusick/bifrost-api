import { useState, useEffect, useCallback, useRef } from "react";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Loader2, Upload, Palette, RotateCcw, Type } from "lucide-react";
import {
	updateBranding,
	uploadLogo,
	resetLogo,
	resetColor,
	resetApplicationName,
	getBranding,
} from "@/hooks/useBranding";
import { createBrandPalette } from "@/lib/brand-palette";
import { applyBrandingTheme, type BrandingSettings } from "@/lib/branding";
import {
	DEFAULT_TERMINOLOGY,
	mergeTerminology,
	serializeTerminology,
	type BrandingTerminologyInput,
	type ProductTermKey,
	type Terminology,
} from "@/lib/terminology";
import { useOrgScope } from "@/contexts/OrgScopeContext";
import type { components } from "@/lib/v1";
import { SettingsReadError } from "./SettingsReadError";

const TERMINOLOGY_ROWS: Array<{
	key: ProductTermKey;
	label: string;
	description: string;
}> = [
	{
		key: "app",
		label: "Apps / Applications",
		description: "Main built experiences, e.g. Games",
	},
	{
		key: "agent",
		label: "Agents",
		description: "AI workers or personas, e.g. Characters",
	},
	{
		key: "form",
		label: "Forms",
		description: "Guided workflow launch interfaces",
	},
];

const DEFAULT_PREVIEW_PRIMARY_COLOR = createBrandPalette(null).light.primary;
const primaryColorPlaceholder = DEFAULT_PREVIEW_PRIMARY_COLOR;

function hydrateBrandingDrafts(
	data: components["schemas"]["BrandingSettings"] | null,
	setBranding: (
		value: components["schemas"]["BrandingSettings"] | null,
	) => void,
	setPrimaryColor: (value: string) => void,
	setHasCustomPrimaryColor: (value: boolean) => void,
	setApplicationName: (value: string) => void,
	setTerminology: (value: Terminology) => void,
) {
	setBranding(data);
	setPrimaryColor(data?.primary_color || DEFAULT_PREVIEW_PRIMARY_COLOR);
	setHasCustomPrimaryColor(Boolean(data?.primary_color));
	setApplicationName(data?.application_name ?? "");
	setTerminology(
		mergeTerminology(data?.terminology as BrandingTerminologyInput),
	);
}

function brandingPrimaryColorUpdate(
	primaryColor: string,
	hasCustomPrimaryColor: boolean,
) {
	return hasCustomPrimaryColor ? { primary_color: primaryColor } : {};
}

export function Branding() {
	const { refreshBranding } = useOrgScope();
	const [branding, setBranding] = useState<
		components["schemas"]["BrandingSettings"] | null
	>(null);
	const [readPending, setReadPending] = useState(true);
	const [readError, setReadError] = useState(false);
	const [hasLoadedBranding, setHasLoadedBranding] = useState(false);
	const [saving, setSaving] = useState(false);
	const [savingTerminology, setSavingTerminology] = useState(false);
	const [savingApplicationName, setSavingApplicationName] = useState(false);
	const [uploading, setUploading] = useState<"square" | "rectangle" | null>(
		null,
	);
	const [resetting, setResetting] = useState<
		"square" | "rectangle" | "color" | "application-name" | null
	>(null);
	const [primaryColor, setPrimaryColor] = useState(
		DEFAULT_PREVIEW_PRIMARY_COLOR,
	);
	const [hasCustomPrimaryColor, setHasCustomPrimaryColor] = useState(false);
	const [applicationName, setApplicationName] = useState("");
	const [terminology, setTerminology] =
		useState<Terminology>(DEFAULT_TERMINOLOGY);
	const refreshBrandingRef = useRef(refreshBranding);
	const readInFlightRef = useRef(false);

	useEffect(() => {
		refreshBrandingRef.current = refreshBranding;
	}, [refreshBranding]);

	const loadBranding = useCallback(
		async ({
			background = false,
			hydrateDrafts = true,
		}: { background?: boolean; hydrateDrafts?: boolean } = {}) => {
			if (readInFlightRef.current) {
				return;
			}
			readInFlightRef.current = true;
			setReadPending(true);

			try {
				const data = await getBranding();
				setReadError(false);
				setBranding(data);
				if (hydrateDrafts) {
					hydrateBrandingDrafts(
						data,
						setBranding,
						setPrimaryColor,
						setHasCustomPrimaryColor,
						setApplicationName,
						setTerminology,
					);
				}
				if (background && data) {
					applyBrandingTheme(data as BrandingSettings);
					refreshBrandingRef.current();
				}
				setHasLoadedBranding(true);
			} catch {
				setReadError(true);
			} finally {
				readInFlightRef.current = false;
				setReadPending(false);
			}
		},
		[],
	);

	// Drag states
	const [dragActiveSquare, setDragActiveSquare] = useState(false);
	const [dragActiveRectangle, setDragActiveRectangle] = useState(false);

	// Load current branding
	useEffect(() => {
		const timer = window.setTimeout(() => {
			void loadBranding({ hydrateDrafts: true });
		}, 0);
		return () => window.clearTimeout(timer);
	}, [loadBranding]);

	// Update primary color
	const handleColorUpdate = async () => {
		if (readError || readPending) {
			return;
		}
		setSaving(true);
		try {
			const updated = await updateBranding({
				...brandingPrimaryColorUpdate(
					primaryColor,
					hasCustomPrimaryColor,
				),
				terminology: serializeTerminology(terminology),
			});
			setBranding(updated);
			setHasCustomPrimaryColor(Boolean(updated.primary_color));
			applyBrandingTheme(updated as BrandingSettings);
			refreshBranding();

			toast.success("Branding updated", {
				description: "Primary color has been updated successfully",
			});
		} catch (err) {
			toast.error("Error", {
				description:
					err instanceof Error
						? err.message
						: "Failed to update branding",
			});
		} finally {
			setSaving(false);
		}
	};

	const handleTerminologyUpdate = async () => {
		if (readError || readPending) {
			return;
		}
		setSavingTerminology(true);
		try {
			const updated = await updateBranding({
				...brandingPrimaryColorUpdate(
					primaryColor,
					hasCustomPrimaryColor,
				),
				terminology: serializeTerminology(terminology),
			});
			setBranding(updated);
			setTerminology(
				mergeTerminology(
					updated.terminology as BrandingTerminologyInput,
				),
			);
			applyBrandingTheme(updated as BrandingSettings);
			refreshBranding();

			toast.success("Terminology updated", {
				description: "Product labels have been updated successfully",
			});
		} catch (err) {
			toast.error("Error", {
				description:
					err instanceof Error
						? err.message
						: "Failed to update terminology",
			});
		} finally {
			setSavingTerminology(false);
		}
	};

	const handleApplicationNameUpdate = async () => {
		if (readError || readPending) {
			return;
		}
		const trimmed = applicationName.trim();
		setSavingApplicationName(true);
		try {
			// Empty input clears the custom name back to the default.
			const updated = trimmed
				? await updateBranding({ application_name: trimmed })
				: await resetApplicationName();
			setBranding(updated);
			setApplicationName(updated.application_name ?? "");
			refreshBranding();

			toast.success("Application name updated", {
				description: trimmed
					? `Now showing "${trimmed}"`
					: "Reverted to the default name",
			});
		} catch (err) {
			toast.error("Error", {
				description:
					err instanceof Error
						? err.message
						: "Failed to update application name",
			});
		} finally {
			setSavingApplicationName(false);
		}
	};

	const handleResetApplicationName = async () => {
		if (readError || readPending) {
			return;
		}
		setResetting("application-name");
		try {
			const updated = await resetApplicationName();
			setBranding(updated);
			setApplicationName(updated.application_name ?? "");
			refreshBranding();

			toast.success("Application name reset", {
				description: "Reverted to the default name",
			});
		} catch (err) {
			toast.error("Error", {
				description:
					err instanceof Error
						? err.message
						: "Failed to reset application name",
			});
		} finally {
			setResetting(null);
		}
	};

	const updateTerm = (
		key: ProductTermKey,
		field: "singular" | "plural",
		value: string,
	) => {
		setTerminology((current) =>
			mergeTerminology({
				app: {
					singular: current.app.singular,
					plural: current.app.plural,
				},
				agent: {
					singular: current.agent.singular,
					plural: current.agent.plural,
				},
				form: {
					singular: current.form.singular,
					plural: current.form.plural,
				},
				[key]: {
					singular:
						field === "singular" ? value : current[key].singular,
					plural: field === "plural" ? value : current[key].plural,
				},
			}),
		);
	};

	// Handle file upload
	const handleLogoUpload = useCallback(
		async (type: "square" | "rectangle", file: File) => {
			if (readError || readPending) {
				return;
			}
			// Validate file type
			if (!file.type.startsWith("image/")) {
				toast.error("Invalid file type", {
					description:
						"Please upload an image file (PNG, JPG, or SVG)",
				});
				return;
			}

			// Validate file size (5MB)
			if (file.size > 5 * 1024 * 1024) {
				toast.error("File too large", {
					description: "Please upload an image smaller than 5MB",
				});
				return;
			}

			setUploading(type);
			try {
				await uploadLogo(type, file);
				await loadBranding({
					background: true,
					hydrateDrafts: false,
				});

				toast.success("Logo uploaded", {
					description: `${
						type === "square" ? "Square" : "Rectangle"
					} logo has been updated successfully`,
				});
			} catch (err) {
				toast.error("Error", {
					description:
						err instanceof Error
							? err.message
							: "Failed to upload logo",
				});
			} finally {
				setUploading(null);
			}
		},
		[loadBranding, readError, readPending],
	);

	// Drag and drop handlers
	const handleDrag = useCallback(
		(e: React.DragEvent, type: "square" | "rectangle") => {
			e.preventDefault();
			e.stopPropagation();
			if (e.type === "dragenter" || e.type === "dragover") {
				if (type === "square") setDragActiveSquare(true);
				else setDragActiveRectangle(true);
			} else if (e.type === "dragleave") {
				if (type === "square") setDragActiveSquare(false);
				else setDragActiveRectangle(false);
			}
		},
		[],
	);

	const handleDrop = useCallback(
		(e: React.DragEvent, type: "square" | "rectangle") => {
			e.preventDefault();
			e.stopPropagation();
			if (type === "square") setDragActiveSquare(false);
			else setDragActiveRectangle(false);

			if (e.dataTransfer.files && e.dataTransfer.files[0]) {
				handleLogoUpload(type, e.dataTransfer.files[0]);
			}
		},
		[handleLogoUpload],
	);

	const handleFileInput = useCallback(
		(
			e: React.ChangeEvent<HTMLInputElement>,
			type: "square" | "rectangle",
		) => {
			const file = e.target.files?.[0];
			if (file) {
				handleLogoUpload(type, file);
			}
		},
		[handleLogoUpload],
	);

	// Reset handlers
	const handleResetLogo = useCallback(
		async (type: "square" | "rectangle") => {
			if (readError || readPending) {
				return;
			}
			setResetting(type);
			try {
				const updated = await resetLogo(type);
				setBranding(updated);
				applyBrandingTheme(updated as BrandingSettings);
				refreshBranding();

				toast.success("Logo reset", {
					description: `${
						type === "square" ? "Square" : "Rectangle"
					} logo has been reset to default`,
				});
			} catch (err) {
				toast.error("Error", {
					description:
						err instanceof Error
							? err.message
							: "Failed to reset logo",
				});
			} finally {
				setResetting(null);
			}
		},
		[readError, readPending, refreshBranding],
	);

	const handleResetColor = useCallback(async () => {
		if (readError || readPending) {
			return;
		}
		setResetting("color");
		try {
			const updated = await resetColor();
			setBranding(updated);
			setPrimaryColor(
				updated.primary_color || DEFAULT_PREVIEW_PRIMARY_COLOR,
			);
			setHasCustomPrimaryColor(Boolean(updated.primary_color));
			applyBrandingTheme(updated as BrandingSettings);
			refreshBranding();

			toast.success("Color reset", {
				description: "Primary color has been reset to default",
			});
		} catch (err) {
			toast.error("Error", {
				description:
					err instanceof Error
						? err.message
						: "Failed to reset color",
			});
		} finally {
			setResetting(null);
		}
	}, [readError, readPending, refreshBranding]);

	if (readPending && !hasLoadedBranding) {
		return (
			<div className="flex items-center justify-center h-64">
				<Loader2 className="h-8 w-8 animate-spin motion-reduce:animate-none" />
			</div>
		);
	}

	if (readError && !hasLoadedBranding) {
		return (
			<SettingsReadError
				resource="branding settings"
				cached={false}
				pending={readPending}
				onRetry={() => void loadBranding()}
			/>
		);
	}

	const previewPalette = createBrandPalette(
		hasCustomPrimaryColor ? primaryColor : null,
	);
	return (
		<div className="space-y-6">
			{readError && hasLoadedBranding ? (
				<SettingsReadError
					resource="branding settings"
					cached
					pending={readPending}
					onRetry={() =>
						void loadBranding({
							background: true,
							hydrateDrafts: false,
						})
					}
				/>
			) : null}
			{/* Application Name */}
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Type className="h-5 w-5" />
						Application Name
					</CardTitle>
					<CardDescription>
						Shown on the login screen, browser tab, and header.
						Leave blank to use the default.
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-4">
					<div className="space-y-2">
						<Label htmlFor="applicationName">Name</Label>
						<Input
							id="applicationName"
							type="text"
							value={applicationName}
							onChange={(e) => setApplicationName(e.target.value)}
							placeholder="Bifrost"
							maxLength={40}
							className="max-w-sm"
						/>
					</div>
					<div className="flex flex-wrap gap-2">
						<Button
							onClick={handleApplicationNameUpdate}
							disabled={
								savingApplicationName ||
								resetting === "application-name" ||
								readError ||
								readPending
							}
							variant="default"
						>
							{savingApplicationName ? (
								<Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
							) : null}
							Update Name
						</Button>
						<Button
							onClick={handleResetApplicationName}
							disabled={
								savingApplicationName ||
								resetting === "application-name" ||
								readError ||
								readPending
							}
							variant="outline"
							size="icon"
							title="Reset to default name"
							aria-label="Reset to default name"
							className="size-11 sm:size-9"
						>
							{resetting === "application-name" ? (
								<Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
							) : (
								<RotateCcw className="h-4 w-4" />
							)}
						</Button>
					</div>
				</CardContent>
			</Card>

			{/* Primary Color */}
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Palette className="h-5 w-5" />
						Primary Color
					</CardTitle>
					<CardDescription>
						Choose your organization's primary brand color
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-4">
					<div className="flex flex-wrap items-center gap-4">
						<div className="space-y-2">
							<Label htmlFor="primaryColor">Color (Hex)</Label>
							<Input
								id="primaryColor"
								type="text"
								value={primaryColor}
								onChange={(e) => {
									setPrimaryColor(e.target.value);
									setHasCustomPrimaryColor(true);
								}}
								placeholder={primaryColorPlaceholder}
								className="w-32 font-mono"
							/>
						</div>
						<div className="space-y-2">
							<Label>Preview</Label>
							<div
								className="h-10 w-20 rounded-[var(--bf-radius-control)] ring-1 ring-border"
								style={{ backgroundColor: primaryColor }}
							/>
						</div>
					</div>
					<div
						className="grid gap-3 sm:grid-cols-2"
						aria-label="Brand appearance preview"
					>
						{(["light", "dark"] as const).map((mode) => (
							<div
								key={mode}
								className="overflow-hidden rounded-[var(--bf-radius-surface)] border"
								style={{
									backgroundColor:
										mode === "light"
											? "#f7f9fa"
											: "#08090b",
									color:
										mode === "light"
											? "#11151a"
											: "#f7f9fb",
								}}
							>
								<div className="flex flex-wrap items-center justify-between gap-2 p-3">
									<span className="text-xs">
										{mode === "light"
											? "Light theme"
											: "Dark theme"}
									</span>
									<span
										className="rounded-[var(--bf-radius-control)] px-3 py-1.5 text-xs font-medium"
										style={{
											backgroundColor:
												previewPalette[mode].primary,
											color: previewPalette[mode]
												.primaryForeground,
										}}
									>
										Primary action
									</span>
								</div>
								<div
									role="img"
									aria-label={`${mode} theme activity gradient`}
									className="h-1"
									style={{
										background:
											previewPalette[mode]
												.activityGradient,
									}}
								/>
							</div>
						))}
					</div>
					<p className="text-xs text-muted-foreground">
						Action colors and activity gradients adapt to your brand
						in each theme.
					</p>
					<div className="flex flex-wrap gap-2">
						<Button
							onClick={handleColorUpdate}
							disabled={
								saving ||
								resetting === "color" ||
								readError ||
								readPending
							}
							variant="default"
						>
							{saving ? (
								<Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
							) : null}
							Update Color
						</Button>
						<Button
							onClick={handleResetColor}
							disabled={
								saving ||
								resetting === "color" ||
								readError ||
								readPending
							}
							variant="outline"
							size="icon"
							title="Reset to default color"
							aria-label="Reset to default color"
							className="size-11 sm:size-9"
						>
							{resetting === "color" ? (
								<Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
							) : (
								<RotateCcw className="h-4 w-4" />
							)}
						</Button>
					</div>
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<CardTitle>Product Terminology</CardTitle>
					<CardDescription>
						Rename fixed platform nouns before the UI renders
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-5">
					<div className="space-y-4">
						{TERMINOLOGY_ROWS.map((row) => (
							<div
								key={row.key}
								className="grid gap-3 md:grid-cols-[minmax(0,1fr)_160px_160px]"
							>
								<div className="space-y-1">
									<Label>{row.label}</Label>
									<p className="text-sm text-muted-foreground">
										{row.description}
									</p>
								</div>
								<div className="space-y-2">
									<Label htmlFor={`${row.key}-singular`}>
										Singular
									</Label>
									<Input
										id={`${row.key}-singular`}
										value={terminology[row.key].singular}
										onChange={(e) =>
											updateTerm(
												row.key,
												"singular",
												e.target.value,
											)
										}
									/>
								</div>
								<div className="space-y-2">
									<Label htmlFor={`${row.key}-plural`}>
										Plural
									</Label>
									<Input
										id={`${row.key}-plural`}
										value={terminology[row.key].plural}
										onChange={(e) =>
											updateTerm(
												row.key,
												"plural",
												e.target.value,
											)
										}
									/>
								</div>
							</div>
						))}
					</div>
					<div className="flex flex-wrap gap-2">
						<Button
							onClick={handleTerminologyUpdate}
							disabled={
								savingTerminology || readError || readPending
							}
						>
							{savingTerminology ? (
								<Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
							) : null}
							Update Terminology
						</Button>
					</div>
				</CardContent>
			</Card>

			{/* Logos */}
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Upload className="h-5 w-5" />
						Brand Logos
					</CardTitle>
					<CardDescription>
						Upload logos for your organization (PNG, JPG, or SVG,
						max 5MB)
					</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
						{/* Square Logo */}
						<div className="space-y-3">
							<div className="flex items-center justify-between">
								<Label>Square Logo (1:1 ratio)</Label>
								{branding?.square_logo_url && (
									<Button
										size="sm"
										variant="ghost"
										onClick={(e) => {
											e.stopPropagation();
											handleResetLogo("square");
										}}
										aria-label="Reset square logo"
										disabled={
											uploading === "square" ||
											resetting === "square" ||
											readError ||
											readPending
										}
									>
										{resetting === "square" ? (
											<Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
										) : (
											<RotateCcw className="h-4 w-4" />
										)}
									</Button>
								)}
							</div>
							<p className="text-xs text-muted-foreground">
								Recommended: 512×512 px
							</p>
							<div
								className={`relative border-2 border-dashed rounded-[var(--bf-radius-surface)] p-6 transition-colors duration-[var(--bf-motion-feedback)] motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring h-48 flex items-center justify-center ${
									dragActiveSquare
										? "border-primary bg-primary/5"
										: "border-border"
								} ${
									uploading === "square" ||
									resetting === "square"
										? "opacity-50 pointer-events-none"
										: readError || readPending
											? "opacity-50 pointer-events-none"
											: "cursor-pointer hover:border-primary/50"
								}`}
								role="button"
								aria-label="Upload square logo"
								aria-disabled={
									uploading === "square" ||
									resetting === "square" ||
									readError ||
									readPending
								}
								tabIndex={
									uploading === "square" ||
									resetting === "square" ||
									readError ||
									readPending
										? -1
										: 0
								}
								onKeyDown={(event) => {
									if (
										(event.key === "Enter" ||
											event.key === " ") &&
										uploading !== "square" &&
										resetting !== "square" &&
										!readError &&
										!readPending
									) {
										event.preventDefault();
										document
											.getElementById("squareLogoInput")
											?.click();
									}
								}}
								onDragEnter={(e) => handleDrag(e, "square")}
								onDragLeave={(e) => handleDrag(e, "square")}
								onDragOver={(e) => handleDrag(e, "square")}
								onDrop={(e) => handleDrop(e, "square")}
								onClick={() =>
									!readError &&
									!readPending &&
									document
										.getElementById("squareLogoInput")
										?.click()
								}
							>
								<input
									id="squareLogoInput"
									type="file"
									accept="image/png,image/jpeg,image/svg+xml"
									onChange={(e) =>
										handleFileInput(e, "square")
									}
									className="hidden"
								/>
								{branding?.square_logo_url ? (
									<div className="flex flex-col items-center gap-3 w-full">
										<img
											src={branding.square_logo_url}
											alt="Square logo"
											className="max-h-24 max-w-24 object-contain"
										/>
										<p className="text-xs text-muted-foreground">
											Click or drag to replace
										</p>
									</div>
								) : (
									<div className="flex flex-col items-center gap-2 text-center">
										<Upload className="h-10 w-10 text-muted-foreground" />
										<p className="text-sm font-medium">
											Drop square logo here
										</p>
										<p className="text-xs text-muted-foreground">
											or click to browse
										</p>
									</div>
								)}
								{uploading === "square" && (
									<div className="absolute inset-0 flex items-center justify-center bg-background/50 rounded-lg">
										<Loader2 className="h-8 w-8 animate-spin motion-reduce:animate-none" />
									</div>
								)}
							</div>
						</div>

						{/* Horizontal Logo */}
						<div className="space-y-3">
							<div className="flex items-center justify-between">
								<Label>Horizontal Logo (~4:1 ratio)</Label>
								{branding?.rectangle_logo_url && (
									<Button
										size="sm"
										variant="ghost"
										onClick={(e) => {
											e.stopPropagation();
											handleResetLogo("rectangle");
										}}
										aria-label="Reset rectangle logo"
										disabled={
											uploading === "rectangle" ||
											resetting === "rectangle" ||
											readError ||
											readPending
										}
									>
										{resetting === "rectangle" ? (
											<Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
										) : (
											<RotateCcw className="h-4 w-4" />
										)}
									</Button>
								)}
							</div>
							<p className="text-xs text-muted-foreground">
								Recommended: 800×200 px
							</p>
							<div
								className={`relative border-2 border-dashed rounded-[var(--bf-radius-surface)] p-6 transition-colors duration-[var(--bf-motion-feedback)] motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring h-48 flex items-center justify-center ${
									dragActiveRectangle
										? "border-primary bg-primary/5"
										: "border-border"
								} ${
									uploading === "rectangle" ||
									resetting === "rectangle"
										? "opacity-50 pointer-events-none"
										: readError || readPending
											? "opacity-50 pointer-events-none"
											: "cursor-pointer hover:border-primary/50"
								}`}
								role="button"
								aria-label="Upload rectangle logo"
								aria-disabled={
									uploading === "rectangle" ||
									resetting === "rectangle" ||
									readError ||
									readPending
								}
								tabIndex={
									uploading === "rectangle" ||
									resetting === "rectangle" ||
									readError ||
									readPending
										? -1
										: 0
								}
								onKeyDown={(event) => {
									if (
										(event.key === "Enter" ||
											event.key === " ") &&
										uploading !== "rectangle" &&
										resetting !== "rectangle" &&
										!readError &&
										!readPending
									) {
										event.preventDefault();
										document
											.getElementById(
												"rectangleLogoInput",
											)
											?.click();
									}
								}}
								onDragEnter={(e) => handleDrag(e, "rectangle")}
								onDragLeave={(e) => handleDrag(e, "rectangle")}
								onDragOver={(e) => handleDrag(e, "rectangle")}
								onDrop={(e) => handleDrop(e, "rectangle")}
								onClick={() =>
									!readError &&
									!readPending &&
									document
										.getElementById("rectangleLogoInput")
										?.click()
								}
							>
								<input
									id="rectangleLogoInput"
									type="file"
									accept="image/png,image/jpeg,image/svg+xml"
									onChange={(e) =>
										handleFileInput(e, "rectangle")
									}
									className="hidden"
								/>
								{branding?.rectangle_logo_url ? (
									<div className="flex flex-col items-center gap-3 w-full">
										<img
											src={branding.rectangle_logo_url}
											alt="Rectangle logo"
											className="max-h-12 max-w-48 object-contain"
										/>
										<p className="text-xs text-muted-foreground">
											Click or drag to replace
										</p>
									</div>
								) : (
									<div className="flex flex-col items-center gap-2 text-center">
										<Upload className="h-10 w-10 text-muted-foreground" />
										<p className="text-sm font-medium">
											Drop rectangle logo here
										</p>
										<p className="text-xs text-muted-foreground">
											or click to browse
										</p>
									</div>
								)}
								{uploading === "rectangle" && (
									<div className="absolute inset-0 flex items-center justify-center bg-background/50 rounded-lg">
										<Loader2 className="h-8 w-8 animate-spin motion-reduce:animate-none" />
									</div>
								)}
							</div>
						</div>
					</div>
				</CardContent>
			</Card>
		</div>
	);
}
