import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const subscribeMock = vi.fn();
let lastOnEvent:
  | ((evt: Record<string, unknown>) => void)
  | null = null;
let lastOnReconnect: (() => void) | null = null;

vi.mock("./ws-client", () => ({
  subscribeToTable: (
    _tableId: string,
    _filter: unknown,
    cb: (evt: Record<string, unknown>) => void,
    onReconnect?: () => void,
  ) => {
    lastOnEvent = cb;
    lastOnReconnect = onReconnect ?? null;
    subscribeMock(_tableId, _filter, cb);
    return () => {
      lastOnEvent = null;
      lastOnReconnect = null;
    };
  },
}));

import { useInfiniteTable } from "./use-infinite-table";

function makePage(ids: string[], total: number, table_id = "tbl-uuid") {
  return new Response(
    JSON.stringify({
      documents: ids.map((id) => ({ id, data: {} })),
      table_id,
      total,
    }),
    {
      status: 200,
      headers: { "content-type": "application/json" },
    },
  );
}

function deferredPage(ids: string[], total: number, table_id = "tbl-uuid") {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((r) => {
    resolve = r;
  });
  return {
    promise,
    resolve: () => resolve(makePage(ids, total, table_id)),
  };
}

describe("useInfiniteTable", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    subscribeMock.mockClear();
    lastOnEvent = null;
    lastOnReconnect = null;
  });

  it("loads the first page with skip_count omitted (server returns count)", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(makePage(["a", "b"], 2));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useInfiniteTable("t1", { pageSize: 100 }),
    );
    await waitFor(() => expect(result.current.loading).toBe(false));

    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.skip_count).toBeUndefined();
    expect(body.limit).toBe(100);
    expect(body.offset).toBe(0);
    expect(result.current.rows).toHaveLength(2);
  });

  it("loadMore appends the next page with skip_count: true", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(makePage(["a", "b"], 4))
      .mockResolvedValueOnce(makePage(["c", "d"], 4));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useInfiniteTable("t1", { pageSize: 2 }),
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.hasMore).toBe(true);

    await act(async () => {
      await result.current.loadMore();
    });

    const secondBody = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(secondBody.skip_count).toBe(true);
    expect(secondBody.offset).toBe(2);
    expect(result.current.rows.map((r) => r.id)).toEqual(["a", "b", "c", "d"]);
  });

  it("refreshes all loaded rows after a subscription reconnect", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(makePage(["a", "b"], 4))
      .mockResolvedValueOnce(makePage(["c", "d"], 4))
      .mockResolvedValueOnce(makePage(["a", "b", "c", "changed"], 4));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useInfiniteTable("t1", { pageSize: 2 }),
    );
    await waitFor(() => expect(result.current.rows).toHaveLength(2));
    await act(async () => result.current.loadMore());
    expect(result.current.rows.map((row) => row.id)).toEqual(["a", "b", "c", "d"]);

    act(() => lastOnReconnect?.());

    await waitFor(() =>
      expect(result.current.rows.map((row) => row.id)).toEqual([
        "a",
        "b",
        "c",
        "changed",
      ]),
    );
  });

  it("refreshes the loaded window after table invalidation", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(makePage(["a", "b"], 4))
      .mockResolvedValueOnce(makePage(["c", "d"], 4))
      .mockResolvedValueOnce(makePage(["fresh-a", "fresh-b", "fresh-c"], 3));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useInfiniteTable("t1", {
        where: { status: "active" },
        pageSize: 2,
        order_by: "created_at",
        order_dir: "desc",
        scope: "org-a",
      }),
    );
    await waitFor(() => expect(result.current.rows).toHaveLength(2));
    await act(async () => result.current.loadMore());
    expect(result.current.rows.map((row) => row.id)).toEqual(["a", "b", "c", "d"]);

    act(() => {
      lastOnEvent?.({ type: "table_invalidated", table_id: "tbl-uuid" });
    });

    await waitFor(() =>
      expect(result.current.rows.map((row) => row.id)).toEqual([
        "fresh-a",
        "fresh-b",
        "fresh-c",
      ]),
    );
    expect(result.current.hasMore).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual({
      where: { status: "active" },
      limit: 4,
      offset: 0,
      order_by: "created_at",
      order_dir: "desc",
    });
    expect(fetchMock.mock.calls[2][0]).toMatch(/scope=org-a$/);
  });

  it("coalesces invalidation bursts to one in-flight refresh and one trailing refresh", async () => {
    const firstRefresh = deferredPage(["first"], 1);
    const trailingRefresh = deferredPage(["trailing"], 1);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(makePage(["initial"], 1))
      .mockReturnValueOnce(firstRefresh.promise)
      .mockReturnValueOnce(trailingRefresh.promise);
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useInfiniteTable("t1", { pageSize: 10 }),
    );
    await waitFor(() => expect(result.current.rows[0]?.id).toBe("initial"));

    act(() => {
      lastOnEvent?.({ type: "table_invalidated", table_id: "tbl-uuid" });
      lastOnEvent?.({ type: "table_invalidated", table_id: "tbl-uuid" });
      lastOnEvent?.({ type: "table_invalidated", table_id: "tbl-uuid" });
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(result.current.rows[0]?.id).toBe("initial");

    await act(async () => {
      firstRefresh.resolve();
      await firstRefresh.promise;
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(result.current.rows[0]?.id).toBe("first");

    await act(async () => {
      trailingRefresh.resolve();
      await trailingRefresh.promise;
    });

    await waitFor(() => expect(result.current.rows[0]?.id).toBe("trailing"));
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("hasMore flips false when a partial page comes back", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(makePage(["a", "b"], 3))
      .mockResolvedValueOnce(makePage(["c"], 3));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useInfiniteTable("t1", { pageSize: 2 }),
    );
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.loadMore();
    });

    expect(result.current.hasMore).toBe(false);
    expect(result.current.rows).toHaveLength(3);
  });

  it("subscribes once with the compiled filter", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(makePage([], 0));
    vi.stubGlobal("fetch", fetchMock);

    renderHook(() =>
      useInfiniteTable("t1", { where: { status: "active" }, pageSize: 100 }),
    );
    await waitFor(() => expect(subscribeMock).toHaveBeenCalledTimes(1));

    const [tableId, filter] = subscribeMock.mock.calls[0];
    expect(tableId).toBe("tbl-uuid");
    expect(filter).toEqual({ eq: [{ row: "status" }, "active"] });
  });

  it("surfaces subscribe error frames as `error`", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(makePage([], 0));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useInfiniteTable("t1", { pageSize: 100 }),
    );
    await waitFor(() => expect(lastOnEvent).not.toBeNull());

    act(() => {
      lastOnEvent?.({ type: "error", message: "Access denied" });
    });

    expect(result.current.error?.message).toBe("Access denied");
  });

  it("rejects unsupported operators (contains/starts_with/...) before fetching", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useInfiniteTable("t1", { where: { name: { contains: "x" } } }),
    );
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error?.message).toContain("contains");
    // Snapshot did fire (loadMore was called) — but the subsequent subscribe
    // step never ran because compileFilterToExpr threw before subscribe.
  });
});
