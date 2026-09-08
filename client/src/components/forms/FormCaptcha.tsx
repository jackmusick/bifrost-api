import { useCallback, useEffect, useId, useRef, useState } from "react";
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import {
	pbkdf2 as altchaPbkdf2,
	solveChallenge,
	type Challenge,
	type DeriveKeyFunction,
} from "altcha/lib";
import { createSHA256, pbkdf2 as wasmPbkdf2 } from "hash-wasm";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { authFetch } from "@/lib/api-client";

interface FormCaptchaProps {
	formId: string;
	onPayloadChange: (payload: string | null) => void;
}

type VerificationState =
	"loading" | "ready" | "verifying" | "verified" | "error";

export const deriveFormCaptchaKey: DeriveKeyFunction = async (
	parameters,
	salt,
	password,
) => {
	if (parameters.algorithm !== "PBKDF2/SHA-256") {
		throw new Error("Unsupported verification algorithm");
	}

	// HTTPS production pages have native WebCrypto, which is substantially
	// faster than evaluating the proof through WASM. Keep the existing WASM
	// implementation for HTTP development origins where subtle crypto is not
	// exposed by the browser.
	if (globalThis.crypto?.subtle) {
		return altchaPbkdf2.deriveKey(parameters, salt, password);
	}

	return {
		derivedKey: await wasmPbkdf2({
			password,
			salt,
			iterations: parameters.cost,
			hashLength: parameters.keyLength ?? 32,
			hashFunction: createSHA256(),
			outputType: "binary",
		}),
	};
};

export function FormCaptcha(props: FormCaptchaProps) {
	return <CaptchaVerification key={props.formId} {...props} />;
}

function CaptchaVerification({ formId, onPayloadChange }: FormCaptchaProps) {
	const verificationId = useId();
	const solveControllerRef = useRef<AbortController | null>(null);
	const [attempt, setAttempt] = useState(0);
	const [challenge, setChallenge] = useState<Challenge | null>(null);
	const [state, setState] = useState<VerificationState>("loading");
	const [error, setError] = useState<string | null>(null);

	const retry = useCallback(() => {
		solveControllerRef.current?.abort();
		onPayloadChange(null);
		setState("loading");
		setError(null);
		setChallenge(null);
		setAttempt((current) => current + 1);
	}, [onPayloadChange]);

	useEffect(() => {
		const requestController = new AbortController();
		solveControllerRef.current?.abort();
		onPayloadChange(null);

		void (async () => {
			try {
				const response = await authFetch(
					`/api/forms/${formId}/captcha/challenge`,
					{ method: "POST", signal: requestController.signal },
				);
				if (!response.ok) throw new Error("Challenge request failed");
				const nextChallenge = (await response.json()) as Challenge;
				if (requestController.signal.aborted) return;
				setChallenge(nextChallenge);
				setState("ready");
			} catch (requestError) {
				if (
					!requestController.signal.aborted &&
					(requestError as Error).name !== "AbortError"
				) {
					setState("error");
					setError("Verification could not be loaded.");
				}
			}
		})();

		return () => {
			requestController.abort();
			solveControllerRef.current?.abort();
		};
	}, [attempt, formId, onPayloadChange]);

	useEffect(
		() => () => {
			solveControllerRef.current?.abort();
		},
		[],
	);

	const verify = async () => {
		if (!challenge || state !== "ready") return;
		const controller = new AbortController();
		solveControllerRef.current = controller;
		setState("verifying");
		setError(null);
		onPayloadChange(null);
		try {
			const solution = await solveChallenge({
				challenge,
				controller,
				deriveKey: deriveFormCaptchaKey,
				timeout: 90_000,
			});
			if (controller.signal.aborted) return;
			if (!solution) throw new Error("Verification timed out");
			const payload = globalThis.btoa(
				JSON.stringify({ challenge, solution }),
			);
			setState("verified");
			onPayloadChange(payload);
		} catch (verificationError) {
			if (
				!controller.signal.aborted &&
				(verificationError as Error).name !== "AbortError"
			) {
				setState("error");
				setError("Verification failed. Try again.");
			}
		}
	};

	return (
		<div
			className="rounded-[var(--bf-radius-surface)] border border-border bg-muted/20 p-4"
			aria-busy={state === "loading" || state === "verifying"}
		>
			<div className="flex min-h-11 items-center gap-3">
				{state === "loading" || state === "verifying" ? (
					<Loader2 className="mt-3 h-5 w-5 shrink-0 self-start motion-safe:animate-spin text-muted-foreground" />
				) : state === "verified" ? (
					<CheckCircle2 className="mt-3 h-5 w-5 shrink-0 self-start text-[var(--bf-success)]" />
				) : (
					<Checkbox
						className="mt-3.5 shrink-0 self-start"
						id={verificationId}
						checked={false}
						disabled={state !== "ready"}
						onCheckedChange={(checked) => {
							if (checked) void verify();
						}}
						aria-label="I'm not a robot"
					/>
				)}
				<div className="min-w-0 flex-1">
					<span role="status" className="sr-only">
						{state === "loading"
							? "Loading verification"
							: state === "verifying"
								? "Verifying"
								: state === "verified"
									? "Verified"
									: ""}
					</span>
					<Label
						htmlFor={
							state === "ready" || state === "error"
								? verificationId
								: undefined
						}
						className="min-h-11 font-medium"
					>
						{state === "loading"
							? "Loading verification…"
							: state === "verifying"
								? "Verifying…"
								: state === "verified"
									? "Verified"
									: "I'm not a robot"}
					</Label>
					<p className="mt-0.5 flex items-center gap-1 text-sm text-muted-foreground">
						<ShieldCheck className="h-4 w-4 shrink-0" /> Private,
						self-hosted spam protection
					</p>
				</div>
			</div>
			{error ? (
				<div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t pt-3">
					<p className="text-sm text-destructive" role="alert">
						{error}
					</p>
					<Button
						type="button"
						variant="outline"
						className="min-h-11"
						onClick={retry}
					>
						Try again
					</Button>
				</div>
			) : null}
		</div>
	);
}
