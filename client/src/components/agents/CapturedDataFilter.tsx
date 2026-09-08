/**
 * Captured Data filter — key/op/value repeater for the agent runs list.
 *
 * Each row: key combobox (populated from the agent's known metadata keys)
 * + op picker (contains / equals, default contains) + value input. When op
 * is 'equals', the value input becomes a combobox of known values for the
 * chosen key. All rows AND together. Scope is per-agent.
 *
 * Parent owns the condition array via `value` / `onChange`; this component
 * is pure UI. Use `conditionsToQueryParam` to serialize into the
 * `metadataFilter` string the runs-list service expects.
 */

import * as React from "react";
import { AlertCircle, Loader2, Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Combobox } from "@/components/ui/combobox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useMetadataKeys, useMetadataValues } from "@/services/agentRuns";

export type MetadataFilterOp = "eq" | "contains";

export interface MetadataFilterCondition {
	key: string;
	op: MetadataFilterOp;
	value: string;
}

export interface CapturedDataFilterProps {
	agentId: string;
	value: MetadataFilterCondition[];
	onChange: (conditions: MetadataFilterCondition[]) => void;
}

/** Serialize conditions into the `metadata_filter` query-string value. */
export function conditionsToQueryParam(
	conditions: MetadataFilterCondition[],
): string | undefined {
	const complete = conditions.filter((c) => c.key && c.value);
	if (complete.length === 0) return undefined;
	return JSON.stringify(complete);
}

export function CapturedDataFilter({
	agentId,
	value,
	onChange,
}: CapturedDataFilterProps) {
	const baseId = React.useId();
	const addButtonRef = React.useRef<HTMLButtonElement>(null);

	function addRow() {
		onChange([...value, { key: "", op: "contains", value: "" }]);
	}
	function updateRow(i: number, patch: Partial<MetadataFilterCondition>) {
		const next = value.map((row, idx) =>
			idx === i ? { ...row, ...patch } : row,
		);
		onChange(next);
	}
	function removeRow(i: number) {
		onChange(value.filter((_, idx) => idx !== i));
		addButtonRef.current?.focus();
	}

	return (
		<section aria-label="Captured data filters" data-testid="captured-data-filter">
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div className="min-w-0 space-y-1">
					<h3 className="text-sm font-semibold leading-6">
						Captured data filters
					</h3>
					{value.length > 0 ? (
						<p className="text-sm leading-5 text-muted-foreground [overflow-wrap:anywhere]">
							Match runs by metadata key and value.
						</p>
					) : null}
				</div>
				<Button
					ref={addButtonRef}
					type="button"
					variant="outline"
					size="lg"
					onClick={addRow}
					className="min-h-11 w-full gap-1.5 sm:w-auto"
					aria-label="Add captured data filter"
				>
					<Plus className="size-4" />
					{value.length === 0 ? "Filter captured data" : "Add another"}
				</Button>
			</div>

			{value.length > 0 ? (
				<div className="space-y-3 pt-3">
					{value.map((row, i) => (
						<ConditionRow
							key={i}
							agentId={agentId}
							baseId={baseId}
							index={i}
							condition={row}
							onChange={(patch) => updateRow(i, patch)}
							onRemove={() => removeRow(i)}
						/>
					))}
				</div>
			) : null}
		</section>
	);
}

interface ConditionRowProps {
	agentId: string;
	baseId: string;
	index: number;
	condition: MetadataFilterCondition;
	onChange: (patch: Partial<MetadataFilterCondition>) => void;
	onRemove: () => void;
}

function ConditionRow({
	agentId,
	baseId,
	index,
	condition,
	onChange,
	onRemove,
}: ConditionRowProps) {
	const keyId = `${baseId}-key-${index}`;
	const opId = `${baseId}-op-${index}`;
	const valueId = `${baseId}-value-${index}`;
	const keyStatusId = `${baseId}-key-status-${index}`;
	const valueStatusId = `${baseId}-value-status-${index}`;
	const rowLabelId = `${baseId}-row-${index}`;

	const {
		data: keysResp,
		isLoading: keysLoading,
		isFetching: keysFetching,
		isError: keysError,
		error: keysErrorObject,
		refetch: refetchKeys,
	} = useMetadataKeys(agentId);
	const {
		data: valuesResp,
		isLoading: valuesLoading,
		isFetching: valuesFetching,
		isError: valuesError,
		error: valuesErrorObject,
		refetch: refetchValues,
	} = useMetadataValues(
		agentId,
		condition.op === "eq" ? condition.key : undefined,
	);
	const keyOptions = (keysResp?.keys ?? []).map((k) => ({
		value: k,
		label: k,
	}));
	const valueOptions = (valuesResp?.values ?? []).map((v) => ({
		value: v,
		label: v,
	}));
	const hasError = keysError || valuesError;
	const isBusy =
		keysLoading ||
		keysFetching ||
		(condition.op === "eq" && (valuesLoading || valuesFetching));
	const rowStateText = getRowStateText({
		condition,
		keysLoading,
		valuesLoading,
	});
	const keyErrorId = `${baseId}-key-error-${index}`;
	const valueErrorId = `${baseId}-value-error-${index}`;

	return (
		<fieldset
			aria-labelledby={rowLabelId}
			aria-busy={isBusy ? "true" : undefined}
			className={cn(
				"space-y-3 rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/20 p-3",
				hasError && "border-[var(--bf-danger)]/30 bg-[var(--bf-danger-soft)]/30",
			)}
		>
			<legend
				id={rowLabelId}
				className="min-w-0 text-sm font-medium leading-6 [overflow-wrap:anywhere]"
			>
				Filter {index + 1}
			</legend>

			<div className="grid gap-3 md:grid-cols-[minmax(0,1.35fr)_minmax(8rem,0.85fr)_minmax(0,1.2fr)_auto] md:items-end">
				<div className="min-w-0 space-y-1.5">
					<Label htmlFor={keyId}>Metadata key</Label>
					<Combobox
						id={keyId}
						aria-describedby={keysError ? keyErrorId : keyStatusId}
						aria-invalid={keysError || undefined}
						options={keyOptions}
						value={condition.key || undefined}
						onValueChange={(v) => onChange({ key: v })}
						placeholder="Pick key…"
						searchPlaceholder="Search keys…"
						emptyText={
							keysLoading
								? "Loading metadata keys…"
								: keysError
									? "Could not load metadata keys."
									: "No metadata keys yet for this agent."
						}
						isLoading={keysLoading || keysFetching}
						className="sm:!min-h-11"
					/>
					{keysError ? (
						<div
							id={keyErrorId}
							role="alert"
							className="flex flex-wrap items-start gap-2 rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/50 px-3 py-2 text-xs leading-5 text-[var(--bf-danger)]"
						>
							<AlertCircle className="mt-0.5 size-3.5 shrink-0" />
							<p className="min-w-0 flex-1">
								Could not load metadata keys{getErrorSuffix(keysErrorObject)}.
							</p>
							<Button
								type="button"
								variant="outline"
								size="sm"
								className="min-h-11 shrink-0"
								disabled={keysFetching}
								onClick={() => {
									void refetchKeys();
								}}
								aria-label="Retry metadata keys"
							>
								Retry
							</Button>
						</div>
					) : (
						<p
							id={keyStatusId}
							role="status"
							className="min-h-5 text-xs leading-5 text-muted-foreground"
						>
							{keysLoading ? (
								<span className="inline-flex items-center gap-1.5">
									<Loader2 className="size-3.5 animate-spin motion-reduce:animate-none" />
									Loading metadata keys for this agent.
								</span>
							) : keysResp?.keys?.length ? (
								"Select a key to enable exact-match value lookup."
							) : (
								"No metadata keys are recorded yet."
							)}
						</p>
					)}
				</div>

				<div className="min-w-0 space-y-1.5">
					<Label htmlFor={opId}>Match mode</Label>
					<Select
						value={condition.op}
						onValueChange={(v) => onChange({ op: v as MetadataFilterOp })}
					>
						<SelectTrigger
							id={opId}
							className="min-h-11 min-w-0 w-full"
							aria-label="Captured data filter operator"
						>
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							<SelectItem className="min-h-11 whitespace-normal [overflow-wrap:anywhere]" value="contains">
								contains
							</SelectItem>
							<SelectItem className="min-h-11 whitespace-normal [overflow-wrap:anywhere]" value="eq">
								equals
							</SelectItem>
						</SelectContent>
					</Select>
				</div>

				<div className="min-w-0 space-y-1.5">
					<Label htmlFor={valueId}>Value</Label>
					{condition.op === "eq" ? (
						<Combobox
							id={valueId}
							aria-describedby={valuesError ? valueErrorId : valueStatusId}
							aria-invalid={valuesError || undefined}
							options={valueOptions}
							value={condition.value || undefined}
							onValueChange={(v) => onChange({ value: v })}
							placeholder="Pick value…"
							searchPlaceholder="Search values…"
							emptyText={
								valuesLoading
									? "Loading values…"
									: valuesError
										? "Could not load values for this key."
									: condition.key
										? "No values recorded."
										: "Pick a key first."
							}
							isLoading={valuesLoading || valuesFetching}
							disabled={!condition.key}
							className="sm:!min-h-11"
						/>
					) : (
						<Input
							id={valueId}
							value={condition.value}
							onChange={(e) => onChange({ value: e.target.value })}
							placeholder="substring…"
							className="min-h-11"
							aria-describedby={valueStatusId}
							aria-label="Captured data filter value"
						/>
					)}
					{valuesError ? (
						<div
							id={valueErrorId}
							role="alert"
							className="flex flex-wrap items-start gap-2 rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/50 px-3 py-2 text-xs leading-5 text-[var(--bf-danger)]"
						>
							<AlertCircle className="mt-0.5 size-3.5 shrink-0" />
							<p className="min-w-0 flex-1">
								Could not load values{getErrorSuffix(valuesErrorObject)}.
							</p>
							<Button
								type="button"
								variant="outline"
								size="sm"
								className="min-h-11 shrink-0"
								disabled={valuesFetching}
								onClick={() => {
									void refetchValues();
								}}
								aria-label="Retry values"
							>
								Retry
							</Button>
						</div>
					) : (
						<p
							id={valueStatusId}
							role="status"
							className="min-h-5 text-xs leading-5 text-muted-foreground"
						>
							{rowStateText}
						</p>
					)}
				</div>

				<div className="flex min-w-0 md:justify-end">
					<Button
						type="button"
						variant="ghost"
						size="icon-lg"
						onClick={onRemove}
						aria-label={`Remove filter row ${index + 1}`}
						className="shrink-0 text-muted-foreground hover:text-foreground"
						>
							<X className="size-4" />
						</Button>
					</div>
				</div>
		</fieldset>
	);
}

function getRowStateText({
	condition,
	keysLoading,
	valuesLoading,
}: {
	condition: MetadataFilterCondition;
	keysLoading: boolean;
	valuesLoading: boolean;
}): string {
	if (keysLoading) {
		return "Loading metadata keys for this agent.";
	}
	if (condition.op === "eq" && valuesLoading) {
		return `Loading values for ${condition.key || "the selected key"}.`;
	}
	if (condition.op === "eq" && !condition.key) {
		return "Pick a key first to load exact-match values.";
	}
	if (condition.op === "eq" && condition.value) {
		return "Choose from the agent's recorded values, or clear the field to remove the row.";
	}
	if (condition.value) {
		return "Substring match is case-insensitive.";
	}
	return "Enter any text to match captured metadata.";
}

function getErrorSuffix(error: unknown) {
	if (error instanceof Error && error.message) {
		return `: ${error.message}`;
	}
	return "";
}
