import { useState, type ComponentProps } from "react";
import { SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
	SheetTrigger,
} from "@/components/ui/sheet";
import { EntityAssignmentPanel } from "./EntityAssignmentPanel";

/** Keep mobile assignment within reach of the current selection. */
export function EntityAssignmentSheet(
	props: ComponentProps<typeof EntityAssignmentPanel>,
) {
	const [open, setOpen] = useState(false);
	return (
		<Sheet
			open={open}
			onOpenChange={(next) => {
				if (!props.disabled) setOpen(next);
			}}
		>
			<SheetTrigger asChild>
				<Button
					variant="outline"
					size="lg"
					className="w-full xl:hidden"
					disabled={props.disabled}
				>
					<SlidersHorizontal aria-hidden="true" className="size-4" />
					Change assignment
				</Button>
			</SheetTrigger>
			<SheetContent
				className="w-full overflow-y-auto sm:max-w-lg"
				showCloseButton={!props.disabled}
			>
				<SheetHeader>
					<SheetTitle>Change assignment</SheetTitle>
					<SheetDescription>
						Choose an organization or access setting for your
						selected entities.
					</SheetDescription>
				</SheetHeader>
				<div className="px-4 pb-6">
					<EntityAssignmentPanel {...props} hideInstructions />
				</div>
			</SheetContent>
		</Sheet>
	);
}
