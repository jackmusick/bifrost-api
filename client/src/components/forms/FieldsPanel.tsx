import { useState } from "react";
import { Plus, Pencil, Trash2, ArrowUp, ArrowDown } from "lucide-react";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
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
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FieldConfigDialog } from "./FieldConfigDialog";
import { useFieldManager } from "@/hooks/useFieldManager";
import type { FormField } from "@/lib/client-types";

interface FieldsPanelProps {
	fields: FormField[];
	setFields: (fields: FormField[]) => void;
}

function FieldRow({
	field,
	index,
	count,
	onMove,
	onEdit,
	onRemove,
}: {
	field: FormField;
	index: number;
	count: number;
	onMove: (direction: "up" | "down") => void;
	onEdit: () => void;
	onRemove: () => void;
}) {
	return (
		<li className="min-w-0 rounded-[var(--bf-radius-surface)] border border-border bg-background p-4">
			<div className="min-w-0 space-y-2">
				<p className="font-medium [overflow-wrap:anywhere]">
					{field.label}
				</p>
				<p className="font-mono text-sm text-muted-foreground [overflow-wrap:anywhere]">
					{field.name}
				</p>
				<div className="flex flex-wrap items-center gap-2">
					<Badge variant="secondary">{field.type}</Badge>
					{field.required && (
						<Badge variant="outline">Required</Badge>
					)}
					<span className="text-sm text-muted-foreground">
						{index + 1} of {count}
					</span>
				</div>
			</div>
			<div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3">
				<div className="flex gap-1">
					<Button
						type="button"
						variant="ghost"
						size="icon"
						className="size-11"
						aria-label={`Move ${field.label} up`}
						onClick={() => onMove("up")}
						disabled={index === 0}
					>
						<ArrowUp className="size-4" />
					</Button>
					<Button
						type="button"
						variant="ghost"
						size="icon"
						className="size-11"
						aria-label={`Move ${field.label} down`}
						onClick={() => onMove("down")}
						disabled={index === count - 1}
					>
						<ArrowDown className="size-4" />
					</Button>
				</div>
				<div className="flex gap-1">
					<Button
						type="button"
						variant="ghost"
						size="icon"
						className="size-11"
						aria-label={`Edit ${field.label}`}
						onClick={onEdit}
					>
						<Pencil className="size-4" />
					</Button>
					<Button
						type="button"
						variant="ghost"
						size="icon"
						className="size-11"
						aria-label={`Remove ${field.label}`}
						onClick={onRemove}
					>
						<Trash2 className="size-4" />
					</Button>
				</div>
			</div>
		</li>
	);
}

export function FieldsPanel({ fields, setFields }: FieldsPanelProps) {
	const {
		selectedField,
		isDialogOpen,
		isDeleteDialogOpen,
		deletingFieldLabel,
		openAddDialog,
		openEditDialog,
		closeDialog,
		saveField,
		openDeleteDialog,
		closeDeleteDialog,
		confirmDelete,
		moveUp,
		moveDown,
	} = useFieldManager({ fields, setFields });

	const [announcement, setAnnouncement] = useState("");

	return (
		<>
			<Card>
				<CardHeader>
					<div className="flex flex-wrap items-start justify-between gap-4">
						<div>
							<CardTitle>Form Fields</CardTitle>
							<CardDescription>
								Add and configure fields for your form
							</CardDescription>
						</div>
						<Button
							type="button"
							className="min-h-11"
							onClick={openAddDialog}
						>
							<Plus className="mr-2 h-4 w-4" />
							Add Field
						</Button>
					</div>
				</CardHeader>
				<CardContent>
					{fields.length > 0 ? (
						<ol aria-label="Form fields" className="space-y-3">
							{fields.map((field, index) => (
								<FieldRow
									key={field.name}
									field={field}
									index={index}
									count={fields.length}
									onEdit={() => openEditDialog(index)}
									onRemove={() => openDeleteDialog(index)}
									onMove={(direction) => {
										if (direction === "up") moveUp(index);
										else moveDown(index);
										setAnnouncement(
											`${field.label} moved to position ${index + (direction === "up" ? 0 : 2)} of ${fields.length}.`,
										);
									}}
								/>
							))}
						</ol>
					) : (
						<div className="flex flex-col items-center justify-center py-12 text-center">
							<p className="text-sm text-muted-foreground">
								No fields added yet. Click "Add Field" to get
								started.
							</p>
						</div>
					)}
				</CardContent>
			</Card>

			<p role="status" className="sr-only">
				{announcement}
			</p>

			<FieldConfigDialog
				field={selectedField}
				open={isDialogOpen}
				onClose={closeDialog}
				onSave={saveField}
			/>

			{/* Delete Confirmation Dialog */}
			<AlertDialog
				open={isDeleteDialogOpen}
				onOpenChange={closeDeleteDialog}
			>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>Remove Field</AlertDialogTitle>
						<AlertDialogDescription className="[overflow-wrap:anywhere]">
							Are you sure you want to remove the field "
							{deletingFieldLabel ?? ""}"? This action cannot be
							undone.
						</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel className="min-h-11">
							Cancel
						</AlertDialogCancel>
						<AlertDialogAction
							onClick={confirmDelete}
							className="min-h-11 bg-destructive text-destructive-foreground hover:bg-destructive/90"
						>
							Remove Field
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</>
	);
}
