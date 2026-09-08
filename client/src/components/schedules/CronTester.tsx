import { useState, useEffect, useCallback, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import { AlertCircle, CheckCircle2, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import { authFetch } from "@/lib/api-client";
import { copyToClipboard } from "@/lib/clipboard";
import { getErrorMessage } from "@/lib/api-error";

interface ValidationResult {
	valid: boolean;
	human_readable: string;
	next_runs?: string[];
	interval_seconds?: number;
	warning?: string;
	error?: string;
}

const EXAMPLE_EXPRESSIONS = [
	{ label: "Every 5 min", expression: "*/5 * * * *" },
	{ label: "Hourly", expression: "0 * * * *" },
	{ label: "Daily 9 AM", expression: "0 9 * * *" },
	{ label: "Weekly Mon", expression: "0 0 * * 1" },
];

export function CronTester() {
	const [expression, setExpression] = useState("");
	const [result, setResult] = useState<ValidationResult | null>(null);
	const [copyResult, setCopyResult] = useState<{
		expression: string;
		state: "copying" | "copied" | "error";
	} | null>(null);
	const [isValidating, setIsValidating] = useState(false);
	const copyResetTimerRef = useRef<number | null>(null);
	const isMountedRef = useRef(true);
	const validationRequestIdRef = useRef(0);
	const prefersReducedMotion = useReducedMotion();
	const copyState = copyResult?.expression === expression ? copyResult.state : "idle";

	const validateExpression = useCallback(async (expr: string, requestId: number) => {
		if (!expr.trim()) {
			return;
		}

		if (!isMountedRef.current || requestId !== validationRequestIdRef.current) {
			return;
		}

		setIsValidating(true);
		try {
			const response = await authFetch("/api/schedules/validate", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ expression: expr }),
			});
			const bodyText = await response.text().catch(() => "");
			if (!isMountedRef.current || requestId !== validationRequestIdRef.current) {
				return;
			}
			if (!response.ok) {
				let detail = bodyText.trim();
				try { detail = getErrorMessage(JSON.parse(bodyText), "Validation failed"); } catch { /* Keep plain-text server errors readable. */ }
				const statusText = response.statusText || `HTTP ${response.status}`;
				setResult({
					valid: false,
					human_readable: "Failed to validate",
					error: detail ? `${statusText}: ${detail}` : statusText,
				});
				return;
			}
			try {
				setResult(JSON.parse(bodyText) as ValidationResult);
			} catch {
				setResult({
					valid: false,
					human_readable: "Failed to validate",
					error: "Unable to read validation response",
				});
			}
		} catch {
			if (!isMountedRef.current || requestId !== validationRequestIdRef.current) {
				return;
			}
			setResult({
				valid: false,
				human_readable: "Failed to validate",
				error: "Unable to connect to validation service",
			});
		} finally {
			if (isMountedRef.current && requestId === validationRequestIdRef.current) {
				setIsValidating(false);
			}
		}
	}, []);

	// Debounced validation - only validate non-empty expressions
	useEffect(() => {
		if (!expression.trim()) {
			return;
		}

		const timer = setTimeout(() => {
			void validateExpression(expression, validationRequestIdRef.current);
		}, 500);

		return () => clearTimeout(timer);
	}, [expression, validateExpression]);

	useEffect(() => {
		isMountedRef.current = true;
		return () => {
			isMountedRef.current = false;
			if (copyResetTimerRef.current !== null) {
				window.clearTimeout(copyResetTimerRef.current);
			}
		};
	}, []);

	// Computed result - null when expression is empty
	const displayResult = expression ? result : null;

	const handleExpressionChange = (nextExpression: string) => {
		validationRequestIdRef.current += 1;
		setExpression(nextExpression);
		setResult(null);
		setIsValidating(false);
	};

	const handleCopy = async () => {
		if (!isMountedRef.current || copyState === "copying") return;
		const copyTarget = expression;
		setCopyResult({ expression: copyTarget, state: "copying" });
		const copied = await copyToClipboard(expression);
		if (!isMountedRef.current) return;
		if (!copied) {
			setCopyResult({ expression: copyTarget, state: "error" });
			return;
		}
		setCopyResult({ expression: copyTarget, state: "copied" });
		if (copyResetTimerRef.current !== null) {
			window.clearTimeout(copyResetTimerRef.current);
		}
		copyResetTimerRef.current = window.setTimeout(() => {
			setCopyResult((current) =>
				current?.expression === copyTarget ? null : current,
			);
			copyResetTimerRef.current = null;
		}, 2000);
	};

	const handleRetry = () => {
		validationRequestIdRef.current += 1;
		void validateExpression(expression, validationRequestIdRef.current);
	};

	return (
		<div className="space-y-4">
			<div className="flex items-start gap-2">
				<Input
					placeholder="0 9 * * *"
					aria-label="Cron expression"
					value={expression}
					onChange={(e) => handleExpressionChange(e.target.value)}
					className="min-h-11 min-w-0 flex-1 font-mono"
					aria-describedby="cron-tester-help"
				/>
				{expression && (
					<Button
						variant="outline"
						size="icon-lg"
						onClick={() => void handleCopy()}
						disabled={copyState === "copying"}
						aria-label={
							copyState === "copying"
								? "Copying expression"
								: copyState === "copied"
									? "Copied expression"
									: copyState === "error"
										? "Retry expression copy"
										: "Copy expression"
						}
						title={
							copyState === "copying"
								? "Copying expression"
								: copyState === "copied"
									? "Copied expression"
									: copyState === "error"
										? "Retry expression copy"
										: "Copy expression"
						}
						className="min-h-11 shrink-0"
					>
						{copyState === "copied" ? (
							<Check className="h-4 w-4" />
						) : (
							<Copy className="h-4 w-4" />
						)}
					</Button>
				)}
			</div>

			{copyState === "error" && (
				<p role="alert" className="text-xs leading-5 text-[var(--bf-danger)]">
					Could not copy the cron expression. Try again, or select it manually.
				</p>
			)}

			<p id="cron-tester-help" className="text-xs leading-5 text-muted-foreground">
				Paste a cron expression to validate it and preview the next run times.
			</p>

			{isValidating && (
				<div className="flex items-center gap-2 text-sm text-muted-foreground">
					<AlertCircle
						className={cn(
							"h-4 w-4",
							!prefersReducedMotion && "motion-safe:animate-pulse",
						)}
					/>
					<span>Validating expression…</span>
				</div>
			)}

			{displayResult && (
				<div className="space-y-3" aria-live="polite">
					{displayResult.valid ? (
						<Alert role="status" className="border-[var(--bf-success)]/20 bg-[var(--bf-success-soft)]/60 text-[var(--bf-success)]">
							<CheckCircle2 className="h-4 w-4 text-[var(--bf-success)]" />
							<AlertDescription className="leading-6 text-[var(--bf-success)]">
								{displayResult.human_readable}
							</AlertDescription>
						</Alert>
					) : (
						<Alert className="border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/60 text-[var(--bf-danger)]">
							<AlertCircle className="h-4 w-4 text-[var(--bf-danger)]" />
							<div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
								<AlertDescription className="min-w-0 leading-6 text-[var(--bf-danger)] [overflow-wrap:anywhere]">
									{displayResult.error || displayResult.human_readable}
								</AlertDescription>
								<Button
									type="button"
									variant="outline"
									size="sm"
									className="min-h-11 shrink-0 self-start"
									onClick={handleRetry}
									disabled={isValidating}
								>
									Retry
								</Button>
							</div>
						</Alert>
					)}

					{displayResult.warning && (
						<Alert className="border-[var(--bf-warning)]/20 bg-[var(--bf-warning-soft)]/60 text-[var(--bf-warning)]">
							<AlertCircle className="h-4 w-4 text-[var(--bf-warning)]" />
							<AlertDescription className="leading-6 text-[var(--bf-warning)] [overflow-wrap:anywhere]">
								{displayResult.warning}
							</AlertDescription>
						</Alert>
					)}

					{displayResult.next_runs &&
						displayResult.next_runs.length > 0 && (
							<div>
								<h4 className="mb-2 text-sm font-semibold">Next runs</h4>
								<div className="space-y-1">
									{displayResult.next_runs.map((run, i) => {
										const date = new Date(run);
										return (
											<div
												key={i}
												className="grid grid-cols-[auto_1fr] gap-x-2 text-sm leading-6 sm:grid-cols-[auto_1fr_auto]"
											>
												<span aria-hidden="true" className="row-span-2 text-muted-foreground sm:row-span-1">
													•
												</span>
												<span className="min-w-0 flex-1 [overflow-wrap:anywhere]">
													{date.toLocaleString()}
												</span>
												<span className="col-start-2 text-xs text-muted-foreground sm:col-start-auto">
													(
													{formatDistanceToNow(date, {
														addSuffix: true,
													})}
													)
												</span>
											</div>
										);
									})}
								</div>
							</div>
						)}
				</div>
			)}

			<div>
				<h4 className="mb-2 text-sm font-semibold">Quick examples:</h4>
				<div className="flex flex-wrap gap-2">
					{EXAMPLE_EXPRESSIONS.map((ex) => (
						<Button
							key={ex.expression}
							variant="outline"
							size="sm"
							onClick={() => setExpression(ex.expression)}
							className="min-h-11 text-xs"
						>
							{ex.label}
						</Button>
					))}
				</div>
			</div>
		</div>
	);
}
