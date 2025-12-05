import {
	createContext,
	useContext,
	useState,
	useCallback,
	type ReactNode,
} from "react";

export interface UploadFailure {
	path: string;
	error: string;
}

export interface UploadState {
	isUploading: boolean;
	currentFile: string | null;
	completedCount: number;
	totalCount: number;
	failures: UploadFailure[];
}

interface UploadProgressContextValue {
	state: UploadState;
	startUpload: (totalFiles: number) => void;
	updateProgress: (currentFile: string, completedCount: number) => void;
	recordFailure: (path: string, error: string) => void;
	finishUpload: () => void;
	resetState: () => void;
}

const initialState: UploadState = {
	isUploading: false,
	currentFile: null,
	completedCount: 0,
	totalCount: 0,
	failures: [],
};

const UploadProgressContext = createContext<UploadProgressContextValue | null>(
	null,
);

export function UploadProgressProvider({ children }: { children: ReactNode }) {
	const [state, setState] = useState<UploadState>(initialState);

	const startUpload = useCallback((totalFiles: number) => {
		setState({
			isUploading: true,
			currentFile: null,
			completedCount: 0,
			totalCount: totalFiles,
			failures: [],
		});
	}, []);

	const updateProgress = useCallback(
		(currentFile: string, completedCount: number) => {
			setState((prev) => ({
				...prev,
				currentFile,
				completedCount,
			}));
		},
		[],
	);

	const recordFailure = useCallback((path: string, error: string) => {
		setState((prev) => ({
			...prev,
			failures: [...prev.failures, { path, error }],
		}));
	}, []);

	const finishUpload = useCallback(() => {
		setState((prev) => ({
			...prev,
			isUploading: false,
			currentFile: null,
			completedCount: prev.totalCount,
		}));
	}, []);

	const resetState = useCallback(() => {
		setState(initialState);
	}, []);

	return (
		<UploadProgressContext.Provider
			value={{
				state,
				startUpload,
				updateProgress,
				recordFailure,
				finishUpload,
				resetState,
			}}
		>
			{children}
		</UploadProgressContext.Provider>
	);
}

export function useUploadProgress(): UploadProgressContextValue {
	const context = useContext(UploadProgressContext);
	if (!context) {
		throw new Error(
			"useUploadProgress must be used within an UploadProgressProvider",
		);
	}
	return context;
}
