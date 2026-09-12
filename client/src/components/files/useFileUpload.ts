import { useRef, useState } from "react";
import { toast } from "sonner";
import { files } from "@/lib/app-sdk/files";

/**
 * Shared upload logic for the explorer: signed-PUT each file to
 * `{location}/{scope}/{prefix}/{name}` via the SDK, then fire `onUploaded` so
 * the listing refetches. Used by both the header Upload button and the
 * folder dropzone/drop handler so the behavior is identical.
 */
export function useFileUpload(
	location: string | null,
	scope: string | null,
	prefix: string,
	onUploaded: () => void,
) {
	const [uploading, setUploading] = useState(false);
	const [progress, setProgress] = useState<string | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [pendingDestination, setPendingDestination] = useState<string | null>(
		null,
	);
	const activeUploadRef = useRef(false);
	const retryBatchRef = useRef<{
		location: string;
		scope: string | null;
		prefix: string;
		files: Array<{ file: File; targetPath: string }>;
	} | null>(null);

	function normalizePrefix(value: string) {
		return value.replace(/\/+$/, "");
	}

	function buildTargetPath(value: string, fileName: string) {
		const cleanedPrefix = normalizePrefix(value);
		return cleanedPrefix ? `${cleanedPrefix}/${fileName}` : fileName;
	}

	function describeDestination(value: string, path: string) {
		const cleanedPrefix = normalizePrefix(path);
		return cleanedPrefix ? `${value}/${cleanedPrefix}` : value;
	}

	function buildBatch(fileList: FileList | File[]) {
		const seen = new Set<string>();
		const filesToUpload: Array<{ file: File; targetPath: string }> = [];
		for (const file of Array.from(fileList)) {
			const targetPath = buildTargetPath(prefix, file.name);
			if (seen.has(targetPath)) continue;
			seen.add(targetPath);
			filesToUpload.push({ file, targetPath });
		}
		return filesToUpload;
	}

	async function runBatch(batch: {
		location: string;
		scope: string | null;
		prefix: string;
		files: Array<{ file: File; targetPath: string }>;
	}) {
		if (activeUploadRef.current) return;
		activeUploadRef.current = true;
		setUploading(true);
		setError(null);
		setProgress(null);
		setPendingDestination(null);

		const failedFiles: Array<{ file: File; targetPath: string }> = [];
		let failureIndex: number | null = null;
		const destination = describeDestination(batch.location, batch.prefix);

		try {
			for (const [index, item] of batch.files.entries()) {
				setProgress(`Uploading ${item.file.name} to ${destination}…`);
				setPendingDestination(item.targetPath);
				try {
					await files.upload(item.targetPath, item.file, {
						location: batch.location,
						scope: batch.scope,
					});
				} catch (uploadError) {
					failedFiles.push(item);
					failureIndex = index;
					const message =
						uploadError instanceof Error
							? uploadError.message
							: String(uploadError);
					const reason = message.replace(
						/^files\.upload:\s*\d+\s*/,
						"",
					);
					setError(
						`Upload to ${destination} failed at ${item.file.name}: ${reason}. Retry continues in the original folder and scope.`,
					);
					if (index + 1 < batch.files.length) {
						failedFiles.push(...batch.files.slice(index + 1));
					}
					break;
				}
			}

			if (failedFiles.length > 0) {
				retryBatchRef.current = {
					location: batch.location,
					scope: batch.scope,
					prefix: batch.prefix,
					files: failedFiles,
				};
				if (failureIndex !== null) {
					setPendingDestination(batch.files[failureIndex].targetPath);
				}
			} else if (batch.files.length > 0) {
				retryBatchRef.current = null;
				setError(null);
				setPendingDestination(null);
				toast.success("Upload complete");
			}
			if (batch.files.length > failedFiles.length) onUploaded();
		} finally {
			activeUploadRef.current = false;
			setUploading(false);
			setProgress(null);
		}
	}

	async function uploadFiles(fileList: FileList | File[]) {
		if (location === null || activeUploadRef.current) return;
		const batch = {
			location,
			scope,
			prefix,
			files: buildBatch(fileList),
		};
		if (batch.files.length === 0) return;
		retryBatchRef.current = null;
		await runBatch(batch);
	}

	function retryUpload() {
		if (activeUploadRef.current) return;
		const batch = retryBatchRef.current;
		if (!batch || batch.files.length === 0) return;
		void runBatch(batch);
	}

	return {
		uploading,
		uploadFiles,
		progress,
		error,
		retryUpload,
		pendingDestination,
	};
}
