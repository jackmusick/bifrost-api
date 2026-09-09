import { FileCode } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { LogoDropZone } from "@/components/LogoDropZone";
import { ResourceIcon } from "@/components/ResourceIcon";
import { bumpEntityLogo } from "@/components/entityLogoVersions";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogClose,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";

export function FormLogoEditor({
	formId,
	logoUrl,
}: {
	formId: string;
	logoUrl?: string | null;
}) {
	const queryClient = useQueryClient();
	const refreshLogo = () => {
		bumpEntityLogo("form", formId);
		void queryClient.invalidateQueries({ queryKey: ["get", "/api/forms"] });
		void queryClient.invalidateQueries({
			queryKey: [
				"get",
				"/api/forms/{form_id}",
				{ params: { path: { form_id: formId } } },
			],
		});
		void queryClient.invalidateQueries({ queryKey: ["get", "/api/home"] });
	};

	return (
		<Dialog>
			<DialogTrigger asChild>
				<Button
					type="button"
					variant="ghost"
					aria-label="Edit form logo"
					title="Edit form logo"
					className="size-12 shrink-0 p-0"
				>
					<ResourceIcon
						kind="form"
						id={formId}
						logo={logoUrl ?? null}
						size="card"
					/>
				</Button>
			</DialogTrigger>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>Form logo</DialogTitle>
					<DialogDescription>
						Upload a PNG, JPEG, or SVG up to 5 MB. Changes save
						immediately.
					</DialogDescription>
				</DialogHeader>
				<div className="flex justify-center py-4">
					<LogoDropZone
						uploadUrl={`/api/forms/${formId}/logo`}
						deleteUrl={`/api/forms/${formId}/logo`}
						previewUrl={logoUrl ?? `/api/forms/${formId}/logo`}
						fallback={<FileCode className="size-8" />}
						size={128}
						ariaLabel="Upload form logo"
						onChange={refreshLogo}
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
