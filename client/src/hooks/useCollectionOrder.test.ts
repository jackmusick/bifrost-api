import { act, renderHook } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { useCollectionOrder } from "./useCollectionOrder";
const auth = vi.hoisted(() => ({ user: { id: "alice" } }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => auth }));
const collections = [{ id: "a" }, { id: "b" }, { id: "c" }, { id: "d" }];
beforeEach(() => {
	localStorage.clear();
	auth.user = { id: "alice" };
});
it("persists a personal order across mounts without changing hidden positions", () => {
	const { result, unmount } = renderHook(() =>
		useCollectionOrder(collections),
	);
	act(() => result.current.reorder(["c", "a"]));
	expect(result.current.collections.map((c) => c.id)).toEqual([
		"c",
		"b",
		"a",
		"d",
	]);
	unmount();
	const next = renderHook(() => useCollectionOrder(collections));
	expect(next.result.current.collections.map((c) => c.id)).toEqual([
		"c",
		"b",
		"a",
		"d",
	]);
});
it("isolates accounts and appends new collections", () => {
	localStorage.setItem(
		"bifrost:collection-order:alice",
		JSON.stringify(["c", "a"]),
	);
	const { result, rerender } = renderHook(() =>
		useCollectionOrder(collections),
	);
	expect(result.current.collections.map((c) => c.id)).toEqual([
		"c",
		"a",
		"b",
		"d",
	]);
	auth.user = { id: "bob" };
	rerender();
	expect(result.current.collections).toEqual(collections);
});
it("recovers from malformed storage and synchronizes mounted consumers", () => {
	localStorage.setItem("bifrost:collection-order:alice", "broken");
	const first = renderHook(() => useCollectionOrder(collections));
	const second = renderHook(() => useCollectionOrder(collections));
	expect(first.result.current.collections).toEqual(collections);
	act(() => first.result.current.reorder(["d", "c", "b", "a"]));
	expect(second.result.current.collections.map((c) => c.id)).toEqual([
		"d",
		"c",
		"b",
		"a",
	]);
});
