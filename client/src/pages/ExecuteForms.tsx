import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { PlayCircle, FileCode, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useForms } from "@/hooks/useForms";
import { useAuth } from "@/hooks/useAuth";

export function ExecuteForms() {
	const navigate = useNavigate();
	const { isPlatformAdmin } = useAuth();
	const { data: forms, isLoading } = useForms();

	// Filter only active forms
	const activeForms = useMemo(() => {
		return forms?.filter((form) => form.is_active) || [];
	}, [forms]);

	// Build validation map from backend-provided missing_required_params
	const formValidation = useMemo(() => {
		const validationMap = new Map<
			string,
			{ valid: boolean; missingParams: string[] }
		>();

		activeForms.forEach((form) => {
			const formWithParams = form as typeof form & {
				missing_required_params?: string[];
			};
			const missingParams = formWithParams.missing_required_params || [];
			validationMap.set(form.id, {
				valid: missingParams.length === 0,
				missingParams,
			});
		});

		return validationMap;
	}, [activeForms]);

	// Filter out invalid forms for regular users
	const visibleForms = useMemo(() => {
		if (isPlatformAdmin) {
			return activeForms; // Platform admins see all forms including invalid
		}
		// Regular users only see valid forms
		return activeForms.filter((form) => {
			const validation = formValidation.get(form.id);
			return validation?.valid !== false;
		});
	}, [activeForms, formValidation, isPlatformAdmin]);

	const handleExecute = (formId: string) => {
		navigate(`/execute/${formId}`);
	};

	return (
		<div className="space-y-6">
			<div>
				<h1 className="text-4xl font-extrabold tracking-tight">
					Execute Forms
				</h1>
				<p className="mt-2 text-muted-foreground">
					Select a form to execute a workflow with a guided interface
				</p>
			</div>

			{isLoading ? (
				<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
					{[...Array(6)].map((_, i) => (
						<Skeleton key={i} className="h-48 w-full" />
					))}
				</div>
			) : visibleForms.length > 0 ? (
				<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
					{visibleForms.map((form) => {
						const validation = formValidation.get(form.id);
						return (
							<Card
								key={form.id}
								className="hover:border-primary transition-colors"
							>
								<CardHeader>
									<div className="flex items-center gap-2">
										<CardTitle className="flex items-center justify-between flex-1">
											{form.name}
											{form.organization_id === null && (
												<Badge
													variant="secondary"
													className="ml-2"
												>
													Global
												</Badge>
											)}
										</CardTitle>
										{!validation?.valid && (
											<Badge
												variant="destructive"
												className="gap-1"
											>
												<AlertTriangle className="h-3 w-3" />
												Invalid
											</Badge>
										)}
									</div>
									{form.description && (
										<CardDescription>
											{form.description}
										</CardDescription>
									)}
								</CardHeader>
								<CardContent className="space-y-4">
									<div>
										<p className="text-sm font-medium text-muted-foreground">
											Workflow
										</p>
										<p className="font-mono text-sm mt-1">
											{form.linked_workflow}
										</p>
									</div>
									<div>
										<p className="text-sm font-medium text-muted-foreground">
											Fields
										</p>
										<p className="text-sm mt-1">
											{(
												form.form_schema as {
													fields?: unknown[];
												} | null
											)?.fields?.length || 0}{" "}
											field
											{(
												form.form_schema as {
													fields?: unknown[];
												} | null
											)?.fields?.length !== 1
												? "s"
												: ""}
										</p>
									</div>
									{!validation?.valid && (
										<div className="pt-2 border-t">
											<span className="text-destructive font-medium text-sm">
												Missing required parameters:
											</span>
											<div className="mt-1 flex flex-wrap gap-1">
												{validation?.missingParams.map(
													(param) => (
														<Badge
															key={param}
															variant="outline"
															className="text-xs font-mono"
														>
															{param}
														</Badge>
													),
												)}
											</div>
										</div>
									)}
									<Button
										className="w-full"
										onClick={() => handleExecute(form.id)}
										disabled={!validation?.valid}
										title={
											!validation?.valid
												? `Cannot execute: Missing required parameters (${validation?.missingParams.join(", ")})`
												: "Execute workflow"
										}
									>
										<PlayCircle className="mr-2 h-4 w-4" />
										Execute Workflow
									</Button>
								</CardContent>
							</Card>
						);
					})}
				</div>
			) : (
				<Card>
					<CardContent className="flex flex-col items-center justify-center py-12 text-center">
						<FileCode className="h-12 w-12 text-muted-foreground" />
						<h3 className="mt-4 text-lg font-semibold">
							No active forms available
						</h3>
						<p className="mt-2 text-sm text-muted-foreground">
							Contact your administrator to create and activate
							forms
						</p>
					</CardContent>
				</Card>
			)}
		</div>
	);
}
