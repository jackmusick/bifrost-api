import { useState } from "react";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { OrganizationSelect } from "@/components/forms/OrganizationSelect";
import { useScopeStore } from "@/stores/scopeStore";

interface RegisterWorkflowDialogProps {
	open: boolean;
	functionName: string;
	onConfirm: (orgId: string | null) => void;
	onCancel: () => void;
}

export function RegisterWorkflowDialog({
	open,
	functionName,
	onConfirm,
	onCancel,
}: RegisterWorkflowDialogProps) {
	return (
		<Dialog open={open} onOpenChange={(isOpen) => !isOpen && onCancel()}>
			<DialogContent className="z-100 sm:max-w-md">
				<DialogHeader>
					<DialogTitle>Register workflow</DialogTitle>
					<DialogDescription>
						Register{" "}
						<code className="font-mono text-sm font-semibold [overflow-wrap:anywhere]">
							{functionName}
						</code>{" "}
						to which organization?
					</DialogDescription>
				</DialogHeader>
				<RegistrationFields onConfirm={onConfirm} onCancel={onCancel} />
			</DialogContent>
		</Dialog>
	);
}

function RegistrationFields({
	onConfirm,
	onCancel,
}: Pick<RegisterWorkflowDialogProps, "onConfirm" | "onCancel">) {
	const scope = useScopeStore((s) => s.scope);
	const [selectedOrgId, setSelectedOrgId] = useState<
		string | null | undefined
	>(scope.orgId ?? null);

	return (
		<>
			<div className="py-2">
				<OrganizationSelect
					aria-label="Organization"
					label="Organization"
					triggerClassName="min-h-11 lg:min-h-11 h-auto"
					value={selectedOrgId}
					onChange={(val) => setSelectedOrgId(val ?? null)}
					showGlobal={true}
					showAll={false}
					contentClassName="z-[101]"
				/>
			</div>
			<DialogFooter>
				<Button
					type="button"
					className="min-h-11"
					variant="outline"
					onClick={onCancel}
				>
					Cancel
				</Button>
				<Button
					type="button"
					className="min-h-11"
					onClick={() => {
						onConfirm(selectedOrgId ?? null);
					}}
				>
					Register
				</Button>
			</DialogFooter>
		</>
	);
}
