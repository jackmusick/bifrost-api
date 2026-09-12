import { useId } from "react";
import { Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface PackageInstallFormProps {
	packageName: string;
	version: string;
	isInstalling: boolean;
	onPackageNameChange: (value: string) => void;
	onVersionChange: (value: string) => void;
	onInstall: () => void;
	onInstallRequirements: () => void;
}

export function PackageInstallForm({
	packageName,
	version,
	isInstalling,
	onPackageNameChange,
	onVersionChange,
	onInstall,
	onInstallRequirements,
}: PackageInstallFormProps) {
	const id = useId();
	return (
		<form
			className="space-y-3 border-b p-3"
			aria-label="Install Python package"
			onSubmit={(event) => {
				event.preventDefault();
				if (!isInstalling && packageName.trim()) onInstall();
			}}
		>
			<div className="space-y-2">
				<Label htmlFor={`${id}-name`}>Package name</Label>
				<Input
					id={`${id}-name`}
					placeholder="e.g., requests"
					value={packageName}
					onChange={(event) =>
						onPackageNameChange(event.target.value)
					}
					disabled={isInstalling}
					className="min-h-11"
					autoCapitalize="none"
					autoCorrect="off"
					spellCheck={false}
				/>
			</div>
			<div className="space-y-2">
				<Label htmlFor={`${id}-version`}>Version (optional)</Label>
				<Input
					id={`${id}-version`}
					placeholder="e.g., 2.31.0"
					value={version}
					onChange={(event) => onVersionChange(event.target.value)}
					disabled={isInstalling}
					className="min-h-11"
					autoCapitalize="none"
					autoCorrect="off"
					spellCheck={false}
				/>
			</div>
			<Button
				type="submit"
				disabled={isInstalling || !packageName.trim()}
				className="min-h-11 h-auto w-full whitespace-normal"
			>
				<Download className="size-4 shrink-0" />
				Install package
			</Button>
			<Button
				type="button"
				onClick={onInstallRequirements}
				disabled={isInstalling}
				variant="outline"
				className="min-h-11 h-auto w-full whitespace-normal"
			>
				<Download className="size-4 shrink-0" />
				Install requirements.txt
			</Button>
			{isInstalling && (
				<p
					role="status"
					className="flex items-start gap-2 text-sm text-muted-foreground"
				>
					<Loader2 className="mt-0.5 size-4 shrink-0 animate-spin motion-reduce:animate-none" />
					<span>Installing packages. Follow progress in Output.</span>
				</p>
			)}
		</form>
	);
}
