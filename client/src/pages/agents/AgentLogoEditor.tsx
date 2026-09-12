import { Bot } from "lucide-react";
import { EntityLogo } from "@/components/EntityLogo";
import { LogoDropZone } from "@/components/LogoDropZone";
import { bumpEntityLogo } from "@/components/entityLogoVersions";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogTrigger,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogDescription,
	DialogFooter,
	DialogClose,
} from "@/components/ui/dialog";

export function AgentLogoEditor({
	agentId,
	logoUrl,
}: {
	agentId: string;
	logoUrl?: string | null;
}) {
	return (
		<Dialog>
			<DialogTrigger asChild>
				<Button
					type="button"
					variant="ghost"
					aria-label="Edit agent logo"
					title="Edit agent logo"
					className="size-12 shrink-0 p-0"
				>
					<EntityLogo
						entityType="agent"
						entityId={agentId}
						logo={logoUrl ?? undefined}
						size={48}
						fallback={<Bot className="h-5 w-5" />}
					/>
				</Button>
			</DialogTrigger>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>Agent logo</DialogTitle>
					<DialogDescription>
						Upload a PNG, JPEG, or SVG up to 5 MB. Changes save
						immediately.
					</DialogDescription>
				</DialogHeader>
				<div className="flex justify-center py-4">
					<LogoDropZone
						uploadUrl={`/api/agents/${agentId}/logo`}
						deleteUrl={`/api/agents/${agentId}/logo`}
						previewUrl={logoUrl ?? `/api/agents/${agentId}/logo`}
						fallback={<Bot className="size-8" />}
						size={128}
						ariaLabel="Upload agent logo"
						onChange={() => bumpEntityLogo("agent", agentId)}
					/>
				</div>
				<DialogFooter>
					<DialogClose asChild>
						<Button
							type="button"
							variant="outline"
							className="min-h-11"
						>
							Done
						</Button>
					</DialogClose>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
