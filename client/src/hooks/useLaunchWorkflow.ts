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
import type { components } from "@/lib/v1";

type Form = components["schemas"]["FormPublic"];

interface UseLaunchWorkflowOptions {
	form: Form;
	/** Additional parameters to pass to launch workflow */
	workflowParams?: Record<string, unknown>;
}

/**
 * Execute launch workflow if form has launchWorkflowId
 *
 * NOTE: The form startup endpoint is currently not implemented in the API.
 * This hook is a placeholder for when that endpoint is available.
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

		// TODO: Implement form startup endpoint when available
		// For now, set empty results so form fields work
		setWorkflowResults({});
	}, [
		form.id,
		form.launch_workflow_id,
		serializedQuery,
		serializedParams,
		setWorkflowResults,
		setIsLoadingLaunchWorkflow,
	]);
}
