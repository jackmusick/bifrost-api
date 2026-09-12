import { SettingsReadError } from "../SettingsReadError";

export function OAuthReadError(props: { cached: boolean; pending: boolean; onRetry: () => void }) {
 return <SettingsReadError resource="SSO configuration" {...props} />;
}
