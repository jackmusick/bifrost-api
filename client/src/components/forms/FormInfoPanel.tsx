import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useId } from "react";
import { cn } from "@/lib/utils";

interface FormInfoPanelProps {
	formName: string;
	setFormName: (name: string) => void;
	formDescription: string;
	setFormDescription: (description: string) => void;
	linkedWorkflow: string;
	setLinkedWorkflow: (workflow: string) => void;
	isGlobal: boolean;
	setIsGlobal: (isGlobal: boolean) => void;
}

export function FormInfoPanel({
	formName,
	setFormName,
	formDescription,
	setFormDescription,
	linkedWorkflow,
	setLinkedWorkflow,
	isGlobal,
	setIsGlobal,
}: FormInfoPanelProps) {
	const id = useId();
	return (
		<Card className="@container min-w-0">
			<CardHeader>
				<CardTitle>Form Information</CardTitle>
				<CardDescription>
					Basic details about the form and linked workflow
				</CardDescription>
			</CardHeader>
			<CardContent className="min-w-0 space-y-5">
				<div className="grid min-w-0 gap-4 @min-[28rem]:grid-cols-2">
					<div className="min-w-0 space-y-2">
						<Label htmlFor={`${id}-formName`}>Form Name *</Label>
						<Input
							className="min-h-11"
							id={`${id}-formName`}
							placeholder="User Onboarding Form"
							value={formName}
							onChange={(e) => setFormName(e.target.value)}
						/>
					</div>

					<div className="min-w-0 space-y-2">
						<Label htmlFor={`${id}-linkedWorkflow`}>
							Linked Workflow *
						</Label>
						<Input
							className="min-h-11 font-mono"
							id={`${id}-linkedWorkflow`}
							placeholder="user_onboarding"
							value={linkedWorkflow}
							onChange={(e) => setLinkedWorkflow(e.target.value)}
						/>
					</div>
				</div>

				<div className="min-w-0 space-y-2">
					<Label htmlFor={`${id}-formDescription`}>Description</Label>
					<Textarea
						className="min-h-28"
						id={`${id}-formDescription`}
						placeholder="Describe what this form does..."
						value={formDescription}
						onChange={(e) => setFormDescription(e.target.value)}
					/>
				</div>

				<fieldset className="min-w-0 space-y-3">
					<legend className="text-sm font-medium">Scope</legend>
					<div className="grid min-w-0 gap-3 @min-[28rem]:grid-cols-2">
						<ScopeChoice
							title="Global"
							description="Available to all organizations"
							selected={isGlobal}
							onSelect={() => setIsGlobal(true)}
						/>
						<ScopeChoice
							title="Organization-Specific"
							description="Specific to one organization"
							selected={!isGlobal}
							onSelect={() => setIsGlobal(false)}
						/>
					</div>
				</fieldset>
			</CardContent>
		</Card>
	);
}

function ScopeChoice({
	title,
	description,
	selected,
	onSelect,
}: {
	title: string;
	description: string;
	selected: boolean;
	onSelect: () => void;
}) {
	return (
		<button
			type="button"
			aria-pressed={selected}
			onClick={onSelect}
			className={cn(
				"min-h-11 min-w-0 rounded-[var(--bf-radius-control)] border p-3 text-left text-sm motion-safe:transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [overflow-wrap:anywhere]",
				selected
					? "border-primary bg-accent text-accent-foreground"
					: "border-border hover:bg-muted",
			)}
		>
			<span className="font-medium">{title}</span>
			<span className="mt-1 block text-sm leading-6 text-muted-foreground">
				{description}
			</span>
		</button>
	);
}
