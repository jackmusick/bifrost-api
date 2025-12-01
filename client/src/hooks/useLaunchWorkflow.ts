/**
 * Hook to execute launch workflow on form load
 *
 * When a form has a launchWorkflowId, this hook:
 * 1. Executes the workflow when the form loads
 * 2. Extracts results into form context
 * 3. Enables field visibility based on workflow results
 */

import { useEffect, useMemo } from "react";
import { useFormContext } from "@/contexts/FormContext";
import { formsService } from "@/services/forms";
import type { components } from "@/lib/v1";
import { toast } from "sonner";

type Form = components["schemas"]["FormRead"];

interface UseLaunchWorkflowOptions {
	form: Form;
	/** Additional parameters to pass to launch workflow */
	workflowParams?: Record<string, unknown>;
}

/**
 * Execute launch workflow if form has launchWorkflowId
 */
export function useLaunchWorkflow({
	form,
	workflowParams = {},
}: UseLaunchWorkflowOptions) {
	const { context, setWorkflowResults, setIsLoadingLaunchWorkflow } =
		useFormContext();

	// Memoize serialized objects for dependency comparison
	const serializedQuery = useMemo(
		() => JSON.stringify(context.query),
		[context.query],
	);
	const serializedParams = useMemo(
		() => JSON.stringify(workflowParams),
		[workflowParams],
	);

	useEffect(() => {
		// Only execute if form has a launch workflow configured
		if (!form.launch_workflow_id) {
			return;
		}

		const executeLaunchWorkflow = async () => {
			try {
				setIsLoadingLaunchWorkflow(true);

				// Merge query params and workflow params for inputData
				// Execute via form startup endpoint (respects form permissions)
				const result = await formsService.executeFormStartup(form.id);

				// Extract workflow result and update context
				const workflowOutput =
					(result.result as Record<string, unknown>) || {};
				setWorkflowResults(workflowOutput);
			} catch (error) {
				// Extract error message from response
				const errorResponse = error as {
					response?: { data?: { message?: string } };
				} & Error;
				const errorMessage =
					errorResponse?.response?.data?.message ||
					errorResponse?.message ||
					"Failed to load form data";

				// Show toast notification
				toast.error(`Launch workflow failed: ${errorMessage}`);

				// On error, set empty results (form fields may hide/show based on missing data)
				setWorkflowResults({});
			} finally {
				setIsLoadingLaunchWorkflow(false);
			}
		};

		executeLaunchWorkflow();
		// Re-run if query params or workflow params change
		// We use serialized versions to deep-compare objects (context.query, workflowParams)
		 
	}, [
		form.id,
		form.launch_workflow_id,
		serializedQuery,
		serializedParams,
		setWorkflowResults,
		setIsLoadingLaunchWorkflow,
	]);
}
