import * as React from "react";
import { Dialog as SheetPrimitive } from "radix-ui";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { XIcon } from "lucide-react";

function Sheet({ ...props }: React.ComponentProps<typeof SheetPrimitive.Root>) {
	return <SheetPrimitive.Root data-slot="sheet" {...props} />;
}

function SheetTrigger({
	...props
}: React.ComponentProps<typeof SheetPrimitive.Trigger>) {
	return <SheetPrimitive.Trigger data-slot="sheet-trigger" {...props} />;
}

function SheetClose({
	...props
}: React.ComponentProps<typeof SheetPrimitive.Close>) {
	return <SheetPrimitive.Close data-slot="sheet-close" {...props} />;
}

function SheetPortal({
	...props
}: React.ComponentProps<typeof SheetPrimitive.Portal>) {
	return <SheetPrimitive.Portal data-slot="sheet-portal" {...props} />;
}

function SheetOverlay({
	className,
	...props
}: React.ComponentProps<typeof SheetPrimitive.Overlay>) {
	return (
		<SheetPrimitive.Overlay
			data-slot="sheet-overlay"
			className={cn(
				"fixed inset-0 z-50 bg-black/30 backdrop-blur-[1px] duration-[var(--bf-motion-disclosure)] [animation-duration:var(--bf-motion-disclosure)] supports-backdrop-filter:backdrop-blur-sm data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0 motion-reduce:animate-none! motion-reduce:transition-none",
				className,
			)}
			{...props}
		/>
	);
}

function SheetContent({
	className,
	children,
	side = "right",
	showCloseButton = true,
	...props
}: React.ComponentProps<typeof SheetPrimitive.Content> & {
	side?: "top" | "right" | "bottom" | "left";
	showCloseButton?: boolean;
}) {
	return (
		<SheetPortal>
			<SheetOverlay />
			<SheetPrimitive.Content
				data-slot="sheet-content"
				data-side={side}
				className={cn(
					"fixed z-50 flex max-h-dvh min-w-0 max-w-full flex-col bg-popover bg-clip-padding text-sm text-popover-foreground shadow-[0_24px_60px_-24px_rgba(15,23,42,0.45)] transition-[transform,opacity,box-shadow] duration-[var(--bf-motion-disclosure)] [animation-duration:var(--bf-motion-disclosure)] ease-in-out data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0 motion-reduce:animate-none! motion-reduce:transition-none",
					// Sizing/position as plain side-conditional classes (NOT data-[side]
					// variants) so consumer className overrides like `sm:max-w-2xl`
					// resolve through tailwind-merge — see ExecutionDrawer, HelpSlideout.
					side === "right" &&
						"inset-y-0 right-0 h-dvh w-full border-l rounded-l-[var(--bf-radius-feature)] border-border/70 sm:max-w-sm data-open:slide-in-from-right-10 data-closed:slide-out-to-right-10",
					side === "left" &&
						"inset-y-0 left-0 h-dvh w-full border-r rounded-r-[var(--bf-radius-feature)] border-border/70 sm:max-w-sm data-open:slide-in-from-left-10 data-closed:slide-out-to-left-10",
					side === "top" &&
						"inset-x-0 top-0 h-auto overflow-y-auto rounded-b-[var(--bf-radius-feature)] border-b border-border/70 data-open:slide-in-from-top-10 data-closed:slide-out-to-top-10",
					side === "bottom" &&
						"inset-x-0 bottom-0 h-auto overflow-y-auto rounded-t-[var(--bf-radius-feature)] border-t border-border/70 data-open:slide-in-from-bottom-10 data-closed:slide-out-to-bottom-10",
					showCloseButton && "[&_[data-slot=sheet-header]]:pr-16",
					className,
				)}
				{...props}
			>
				{children}
				{showCloseButton && (
					<SheetPrimitive.Close data-slot="sheet-close" asChild>
						<Button
							variant="ghost"
							className="absolute top-4 right-4 size-11 bg-secondary sm:size-8"
							size="icon-sm"
						>
							<XIcon className="size-4" />
							<span className="sr-only">Close</span>
						</Button>
					</SheetPrimitive.Close>
				)}
			</SheetPrimitive.Content>
		</SheetPortal>
	);
}

function SheetHeader({ className, ...props }: React.ComponentProps<"div">) {
	return (
		<div
			data-slot="sheet-header"
			className={cn(
				"flex min-w-0 shrink-0 flex-col gap-1.5 p-6",
				className,
			)}
			{...props}
		/>
	);
}

function SheetFooter({ className, ...props }: React.ComponentProps<"div">) {
	return (
		<div
			data-slot="sheet-footer"
			className={cn("mt-auto flex flex-col gap-2 p-6", className)}
			{...props}
		/>
	);
}

function SheetTitle({
	className,
	...props
}: React.ComponentProps<typeof SheetPrimitive.Title>) {
	return (
		<SheetPrimitive.Title
			data-slot="sheet-title"
			className={cn(
				"min-w-0 text-base font-medium leading-snug text-foreground [overflow-wrap:anywhere]",
				className,
			)}
			{...props}
		/>
	);
}

function SheetDescription({
	className,
	...props
}: React.ComponentProps<typeof SheetPrimitive.Description>) {
	return (
		<SheetPrimitive.Description
			data-slot="sheet-description"
			className={cn(
				"min-w-0 text-sm text-muted-foreground [overflow-wrap:anywhere]",
				className,
			)}
			{...props}
		/>
	);
}

export {
	Sheet,
	SheetTrigger,
	SheetClose,
	SheetContent,
	SheetHeader,
	SheetFooter,
	SheetTitle,
	SheetDescription,
};
