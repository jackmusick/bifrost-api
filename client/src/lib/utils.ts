import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/**
 * Parse a date string from the backend, handling UTC timestamps properly.
 * The backend sends ISO strings without 'Z' suffix, which are UTC timestamps.
 * We need to append 'Z' to tell JavaScript they're UTC, not local time.
 * @param dateString - ISO date string from backend
 * @returns Date object in user's local timezone
 */
function parseBackendDate(dateString: string): Date {
    // If the string doesn't end with 'Z' and doesn't have a timezone offset,
    // it's a UTC timestamp from Python's isoformat(), so append 'Z'
    if (!dateString.endsWith('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
        return new Date(dateString + 'Z');
    }
    return new Date(dateString);
}

/**
 * Format a date/time string in the user's local timezone
 * @param dateString - ISO date string or Date object
 * @param options - Intl.DateTimeFormatOptions to customize the output
 * @returns Formatted date string in user's timezone
 */
export function formatDate(
    dateString: string | Date,
    options?: Intl.DateTimeFormatOptions
): string {
    const date = typeof dateString === "string" ? parseBackendDate(dateString) : dateString;

    const defaultOptions: Intl.DateTimeFormatOptions = {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        ...options,
    };

    return date.toLocaleString(undefined, defaultOptions);
}

/**
 * Format a date/time string as a short date (no time)
 * @param dateString - ISO date string or Date object
 * @returns Formatted date string (e.g., "Jan 15, 2025")
 */
export function formatDateShort(dateString: string | Date): string {
    return formatDate(dateString, {
        year: "numeric",
        month: "short",
        day: "numeric",
    });
}

/**
 * Format a date/time string as time only
 * @param dateString - ISO date string or Date object
 * @returns Formatted time string (e.g., "03:45:12 PM")
 */
export function formatTime(dateString: string | Date): string {
    const date = typeof dateString === "string" ? parseBackendDate(dateString) : dateString;
    return date.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    });
}

/**
 * Format a date/time string relative to now (e.g., "2 hours ago", "in 3 days")
 * @param dateString - ISO date string or Date object
 * @returns Relative time string
 */
export function formatRelativeTime(dateString: string | Date): string {
    const date = typeof dateString === "string" ? parseBackendDate(dateString) : dateString;
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (Math.abs(diffSecs) < 60) {
        return "just now";
    } else if (Math.abs(diffMins) < 60) {
        return diffMins > 0 ? `in ${diffMins} min` : `${Math.abs(diffMins)} min ago`;
    } else if (Math.abs(diffHours) < 24) {
        return diffHours > 0 ? `in ${diffHours} hr` : `${Math.abs(diffHours)} hr ago`;
    } else if (Math.abs(diffDays) < 7) {
        return diffDays > 0 ? `in ${diffDays} days` : `${Math.abs(diffDays)} days ago`;
    } else {
        return formatDate(date);
    }
}
