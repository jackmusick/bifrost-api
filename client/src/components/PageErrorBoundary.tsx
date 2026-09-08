import { Component, ErrorInfo, ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardFooter,
	CardHeader,
	CardTitle,
	CardDescription,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface Props {
	children: ReactNode;
	resetKey?: string;
}

interface State {
	hasError: boolean;
	error: Error | null;
}

export class PageErrorBoundary extends Component<Props, State> {
	constructor(props: Props) {
		super(props);
		this.state = { hasError: false, error: null };
	}

	static getDerivedStateFromError(error: Error): Partial<State> {
		return { hasError: true, error };
	}

	componentDidCatch(error: Error, errorInfo: ErrorInfo) {
		if (import.meta.env.DEV) {
			console.error("PageErrorBoundary caught:", error, errorInfo);
		}
	}

	componentDidUpdate(prevProps: Props) {
		if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
			this.setState({ hasError: false, error: null });
		}
	}

	handleReset = () => {
		this.setState({ hasError: false, error: null });
	};

	render() {
		if (this.state.hasError) {
			return (
				<div className="flex min-h-[400px] items-center justify-center p-4">
					<Card className="flex max-h-[calc(100dvh-2rem)] flex-col w-full max-w-lg overflow-hidden">
						<CardHeader className="shrink-0">
							<div className="flex items-center gap-3">
								<div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)] bg-destructive/10">
									<AlertTriangle className="h-5 w-5 text-destructive" />
								</div>
								<div className="min-w-0">
									<CardTitle role="heading" aria-level={2} className="text-pretty text-lg [overflow-wrap:anywhere]">
										Something went wrong
									</CardTitle>
									<CardDescription className="[overflow-wrap:anywhere]">
										This page encountered an error
									</CardDescription>
								</div>
							</div>
						</CardHeader>
						<CardContent className="min-h-0 flex-1 overflow-y-auto">
							<Alert variant="destructive">
								<AlertDescription className="font-mono text-sm [overflow-wrap:anywhere]">
									{this.state.error?.message || "Unknown error"}
								</AlertDescription>
							</Alert>
						</CardContent>
						<CardFooter className="flex shrink-0 flex-col gap-2 sm:flex-row">
							<Button onClick={this.handleReset} className="h-11 w-full sm:w-auto">
								<RotateCcw className="mr-2 h-4 w-4" />
								Try Again
							</Button>
						</CardFooter>
					</Card>
				</div>
			);
		}
		return this.props.children;
	}
}

export function RouteErrorBoundary({ children }: { children: ReactNode }) {
	const location = useLocation();
	return (
		<PageErrorBoundary resetKey={location.pathname}>
			{children}
		</PageErrorBoundary>
	);
}
