import { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RotateCcw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface Props {
	children: ReactNode;
	fallback?: ReactNode;
}

interface State {
	hasError: boolean;
	error: Error | null;
	errorInfo: ErrorInfo | null;
}

/**
 * ErrorBoundary component to catch and handle React errors gracefully
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<Props, State> {
	constructor(props: Props) {
		super(props);
		this.state = {
			hasError: false,
			error: null,
			errorInfo: null,
		};
	}

	static getDerivedStateFromError(error: Error): Partial<State> {
		// Update state so the next render will show the fallback UI
		return { hasError: true, error };
	}

	componentDidCatch(error: Error, errorInfo: ErrorInfo) {
		// Log the error to console in development
		if (import.meta.env.DEV) {
			console.error("ErrorBoundary caught an error:", error, errorInfo);
		}

		// You could also log the error to an error reporting service here
		this.setState({ errorInfo });
	}

	handleReset = () => {
		this.setState({
			hasError: false,
			error: null,
			errorInfo: null,
		});
	};

	handleGoHome = () => {
		window.location.href = "/";
	};

	render() {
		if (this.state.hasError) {
			// Custom fallback UI if provided
			if (this.props.fallback) {
				return this.props.fallback;
			}

			// Default error UI
			return (
				<div className="flex items-center justify-center min-h-screen bg-background p-4">
					<Card className="w-full max-w-2xl">
						<CardHeader>
							<div className="flex items-center gap-3">
								<div className="flex h-12 w-12 items-center justify-center rounded-lg bg-destructive/10">
									<AlertTriangle className="h-6 w-6 text-destructive" />
								</div>
								<div>
									<CardTitle>Something went wrong</CardTitle>
									<CardDescription>
										An unexpected error occurred in the
										application
									</CardDescription>
								</div>
							</div>
						</CardHeader>
						<CardContent className="space-y-4">
							<Alert variant="destructive">
								<AlertDescription className="font-mono text-sm">
									{this.state.error?.message ||
										"Unknown error"}
								</AlertDescription>
							</Alert>

							{import.meta.env.DEV && this.state.errorInfo && (
								<details className="text-sm">
									<summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">
										Error Details (Development Only)
									</summary>
									<pre className="mt-2 overflow-auto rounded-lg bg-muted p-4 text-xs">
										{this.state.error?.stack}
										{"\n\nComponent Stack:\n"}
										{this.state.errorInfo.componentStack}
									</pre>
								</details>
							)}

							<div className="rounded-lg bg-muted p-4">
								<h4 className="font-medium mb-2">
									What you can do:
								</h4>
								<ul className="space-y-1 text-sm text-muted-foreground">
									<li>• Try refreshing the page</li>
									<li>
										• Clear your browser cache and cookies
									</li>
									<li>
										• Contact support if the problem
										persists
									</li>
								</ul>
							</div>
						</CardContent>
						<CardFooter className="flex gap-2">
							<Button
								onClick={this.handleReset}
								variant="default"
							>
								<RotateCcw className="mr-2 h-4 w-4" />
								Try Again
							</Button>
							<Button
								onClick={this.handleGoHome}
								variant="outline"
							>
								<Home className="mr-2 h-4 w-4" />
								Go to Home
							</Button>
						</CardFooter>
					</Card>
				</div>
			);
		}

		return this.props.children;
	}
}
