import type { LucideIcon } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ModelProfileSelector } from "./ModelProfileSelector";

export function ModelAssignmentCard({ assignmentKey, label, description, icon: Icon, profileId, disabled, saving, onChange }: {
	assignmentKey: string;
	label: string;
	description: string;
	icon: LucideIcon;
	profileId: string | null;
	disabled: boolean;
	saving: boolean;
	onChange: (profileId: string) => void;
}) {
	return <Card size="sm" className="min-w-0">
		<CardHeader>
			<CardTitle className="flex items-start gap-2 text-base"><Icon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" /><span className="min-w-0 [overflow-wrap:anywhere]">{label}</span></CardTitle>
			<CardDescription>{description}</CardDescription>
		</CardHeader>
		<CardContent>
			<ModelProfileSelector profileErrorShownByParent id={`assignment-${assignmentKey}`} label={`${label} Profile`} value={profileId} onValueChange={onChange} chatOnly={assignmentKey === "chat_default"} disabled={disabled} isSaving={saving} />
		</CardContent>
	</Card>;
}
