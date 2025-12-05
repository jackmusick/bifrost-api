/**
 * React Query hooks for forms management
 * All hooks use the centralized api client which handles X-Organization-Id automatically
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { formsService } from "@/services/forms";
import type { components } from "@/lib/v1";
import type { FormSubmission } from "@/lib/client-types";

type FormCreate = components["schemas"]["FormCreate"];
type FormUpdate = components["schemas"]["FormUpdate"];
type FormPublic = components["schemas"]["FormPublic"];

import { toast } from "sonner";
import { useScopeStore } from "@/stores/scopeStore";
import { useAuth } from "@/contexts/AuthContext";

export function useForms() {
	const orgId = useScopeStore((state) => state.scope.orgId);
	const { user } = useAuth();

	return useQuery<FormPublic[]>({
		queryKey: ["forms", orgId],
		queryFn: () => formsService.getForms(),
		// Only fetch when authenticated
		enabled: !!user,
		// Don't use cached data from previous scope
		staleTime: 0,
		// Always refetch when component mounts (navigating to page)
		refetchOnMount: "always",
	});
}

export function useForm(formId: string | undefined) {
	return useQuery<FormPublic>({
		queryKey: ["forms", formId],
		queryFn: () => formsService.getForm(formId!),
		enabled: !!formId,
	});
}

export function useCreateForm() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (request: FormCreate) => formsService.createForm(request),
		onSuccess: (_, variables) => {
			queryClient.invalidateQueries({ queryKey: ["forms"] });
			toast.success("Form created", {
				description: `Form "${variables.name}" has been created`,
			});
		},
		onError: (error: Error) => {
			toast.error("Failed to create form", {
				description: error.message,
			});
		},
	});
}

export function useUpdateForm() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: ({
			formId,
			request,
		}: {
			formId: string;
			request: FormUpdate;
		}) => formsService.updateForm(formId, request),
		onSuccess: (_, variables) => {
			queryClient.invalidateQueries({ queryKey: ["forms"] });
			queryClient.invalidateQueries({
				queryKey: ["forms", variables.formId],
			});
			toast.success("Form updated", {
				description: "The form has been updated successfully",
			});
		},
		onError: (error: Error) => {
			toast.error("Failed to update form", {
				description: error.message,
			});
		},
	});
}

export function useDeleteForm() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (formId: string) => formsService.deleteForm(formId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["forms"] });
			toast.success("Form deleted", {
				description: "The form has been deactivated",
			});
		},
		onError: (error: Error) => {
			toast.error("Failed to delete form", {
				description: error.message,
			});
		},
	});
}

export function useSubmitForm() {
	return useMutation({
		mutationFn: (submission: FormSubmission & { orgId?: string }) =>
			formsService.submitForm(submission),
		onSuccess: (data) => {
			toast.success("Workflow execution started", {
				description: `Execution ID: ${data.execution_id}`,
			});
		},
		onError: (error: Error) => {
			toast.error("Failed to submit form", {
				description: error.message,
			});
		},
	});
}
