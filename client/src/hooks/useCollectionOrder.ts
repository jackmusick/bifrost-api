import { useSyncExternalStore } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";

const changed = "bifrost-collection-order-changed";
function subscribe(listener: () => void) {
	window.addEventListener("storage", listener);
	window.addEventListener(changed, listener);
	return () => {
		window.removeEventListener("storage", listener);
		window.removeEventListener(changed, listener);
	};
}

/** Personal browser layout; collection ownership and sharing remain server-owned. */
export function useCollectionOrder<T extends { id: string }>(collections: T[]) {
	const { user } = useAuth();
	const key = user?.id ? `bifrost:collection-order:${user.id}` : null;
	const raw = useSyncExternalStore(
		subscribe,
		() => {
			try {
				return key ? localStorage.getItem(key) : null;
			} catch {
				return null;
			}
		},
		() => null,
	);
	let ids: string[] = [];
	try {
		const parsed: unknown = JSON.parse(raw ?? "[]");
		if (Array.isArray(parsed))
			ids = parsed.filter((id): id is string => typeof id === "string");
	} catch {
		/* Invalid stored preferences fall back to the server order. */
	}
	const rank = new Map(ids.map((id, index) => [id, index]));
	const ordered = [...collections].sort(
		(a, b) => (rank.get(a.id) ?? Infinity) - (rank.get(b.id) ?? Infinity),
	);
	const reorder = (nextIds: string[]) => {
		if (!key) return;
		const known = new Set(collections.map((c) => c.id));
		// A scope-filtered tab strip only changes those positions, preserving hidden tabs.
		const next = [...new Set(nextIds)].filter((id) => known.has(id));
		const moved = new Set(next);
		let index = 0;
		const complete = ordered.map((c) =>
			moved.has(c.id) ? next[index++] : c.id,
		);
		try {
			localStorage.setItem(key, JSON.stringify(complete));
			window.dispatchEvent(new Event(changed));
		} catch {
			toast.error("Could not save collection order in this browser.");
		}
	};
	return { collections: ordered, reorder };
}
