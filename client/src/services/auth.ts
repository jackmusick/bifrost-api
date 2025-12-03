/**
 * Auth Service
 *
 * API methods for authentication, MFA, and OAuth operations.
 *
 * Note: Uses direct fetch calls rather than the typed API client because
 * these auth endpoints were added after the last type generation.
 * Once the API is running, regenerate types with: npm run generate:types
 */

// =============================================================================
// Types
// =============================================================================

export interface OAuthProvider {
	name: string;
	display_name: string;
	icon: string | null;
}

export interface AuthStatus {
	needs_setup: boolean;
	password_login_enabled: boolean;
	mfa_required_for_password: boolean;
	oauth_providers: OAuthProvider[];
}

export interface OAuthInitResponse {
	authorization_url: string;
	state: string;
}

export interface MFAStatus {
	mfa_enabled: boolean;
	mfa_required: boolean;
	enforcement_deadline: string | null;
	enrolled_methods: string[];
	recovery_codes_remaining: number;
}

export interface TOTPSetupResponse {
	secret: string;
	qr_code_uri: string;
	provisioning_uri: string;
	issuer: string;
	account_name: string;
}

export interface TOTPVerifyResponse {
	success: boolean;
	recovery_codes: string[];
}

export interface RecoveryCodesCount {
	total: number;
	remaining: number;
}

export interface TrustedDevice {
	id: string;
	device_name: string | null;
	created_at: string;
	expires_at: string;
	last_used_at: string | null;
	is_current: boolean;
}

// =============================================================================
// Auth Status
// =============================================================================

export async function getAuthStatus(): Promise<AuthStatus> {
	const res = await fetch("/auth/status");
	if (!res.ok) throw new Error("Failed to get auth status");
	return res.json();
}

// =============================================================================
// OAuth Providers
// =============================================================================

/**
 * Get available OAuth providers.
 * Uses the auth status endpoint which includes provider info.
 */
export async function getOAuthProviders(): Promise<OAuthProvider[]> {
	const status = await getAuthStatus();
	return status.oauth_providers;
}

export async function initOAuth(
	provider: string,
	redirectUri: string,
): Promise<OAuthInitResponse> {
	const res = await fetch(
		`/auth/oauth/init/${provider}?redirect_uri=${encodeURIComponent(redirectUri)}`,
	);
	if (!res.ok) throw new Error("Failed to initialize OAuth");
	return res.json();
}

export async function getOAuthVerifier(): Promise<{
	code_verifier: string;
	code_challenge: string;
}> {
	const res = await fetch("/auth/oauth/init/microsoft/verifier");
	if (!res.ok) throw new Error("Failed to get code verifier");
	return res.json();
}

// =============================================================================
// MFA Operations
// =============================================================================

export async function getMFAStatus(): Promise<MFAStatus> {
	const res = await fetch("/auth/mfa/status");
	if (!res.ok) throw new Error("Failed to get MFA status");
	return res.json();
}

export async function setupTOTP(): Promise<TOTPSetupResponse> {
	const res = await fetch("/auth/mfa/setup", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
	});
	if (!res.ok) throw new Error("Failed to setup TOTP");
	return res.json();
}

export async function verifyTOTPSetup(
	code: string,
): Promise<TOTPVerifyResponse> {
	const res = await fetch("/auth/mfa/verify", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ code }),
	});
	if (!res.ok) throw new Error("Failed to verify TOTP");
	return res.json();
}

export async function removeTOTP(
	password?: string,
	mfaCode?: string,
): Promise<void> {
	const res = await fetch("/auth/mfa", {
		method: "DELETE",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ password, mfa_code: mfaCode }),
	});
	if (!res.ok) throw new Error("Failed to remove TOTP");
}

export async function getRecoveryCodesCount(): Promise<RecoveryCodesCount> {
	const res = await fetch("/auth/mfa/recovery-codes/count");
	if (!res.ok) throw new Error("Failed to get recovery codes count");
	return res.json();
}

export async function regenerateRecoveryCodes(
	mfaCode: string,
): Promise<string[]> {
	const res = await fetch("/auth/mfa/recovery-codes/regenerate", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ mfa_code: mfaCode }),
	});
	if (!res.ok) throw new Error("Failed to regenerate recovery codes");
	const data = await res.json();
	return data.recovery_codes;
}

// =============================================================================
// Trusted Devices
// =============================================================================

export async function getTrustedDevices(): Promise<TrustedDevice[]> {
	const res = await fetch("/auth/mfa/trusted-devices");
	if (!res.ok) throw new Error("Failed to get trusted devices");
	const data = await res.json();
	return data.devices;
}

export async function revokeTrustedDevice(deviceId: string): Promise<void> {
	const res = await fetch(`/auth/mfa/trusted-devices/${deviceId}`, {
		method: "DELETE",
	});
	if (!res.ok) throw new Error("Failed to revoke device");
}

export async function revokeAllTrustedDevices(): Promise<void> {
	const res = await fetch("/auth/mfa/trusted-devices", {
		method: "DELETE",
	});
	if (!res.ok) throw new Error("Failed to revoke all devices");
}

// =============================================================================
// User Registration (for setup)
// =============================================================================

export async function registerUser(
	email: string,
	password: string,
	name?: string,
): Promise<void> {
	const res = await fetch("/auth/register", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ email, password, name }),
	});

	if (!res.ok) {
		const error = await res.json().catch(() => ({}));
		throw new Error(error.detail || "Registration failed");
	}
}
