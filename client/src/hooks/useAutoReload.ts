import { useEffect, useRef } from 'react';

/**
 * Hook to automatically reload data when the scope changes
 * Use this for resources that are scoped to organizations
 *
 * @param scope - The current organizational scope (e.g., orgId)
 * @param reloadFn - Function to call when scope changes
 * @param options - Configuration options
 */
export function useAutoReload(
  scope: string | undefined,
  reloadFn: () => void | Promise<void>,
  options: {
    /** Skip reload for unscoped/global resources */
    skipForGlobal?: boolean;
    /** Debounce delay in milliseconds */
    debounceMs?: number;
  } = {}
) {
  const { skipForGlobal = false, debounceMs = 0 } = options;
  const isInitialMount = useRef(true);

  useEffect(() => {
    // Skip reload on initial mount
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    // Skip reload for global scope if configured
    if (skipForGlobal && (!scope || scope === 'GLOBAL')) {
      return;
    }

    // Debounce the reload if configured
    if (debounceMs > 0) {
      const timer = setTimeout(() => {
        void reloadFn();
      }, debounceMs);

      return () => clearTimeout(timer);
    }

    // Execute reload immediately
    void reloadFn();
    return;
  }, [scope, reloadFn, skipForGlobal, debounceMs]);
}

/**
 * Hook to reload data when ANY of multiple dependencies change
 * Useful when data depends on multiple filters or state values
 *
 * @param dependencies - Array of values to watch for changes
 * @param reloadFn - Function to call when any dependency changes
 * @param options - Configuration options
 */
export function useAutoReloadOnChange(
  dependencies: unknown[],
  reloadFn: () => void | Promise<void>,
  options: {
    /** Skip reload on initial mount */
    skipInitial?: boolean;
    /** Debounce delay in milliseconds */
    debounceMs?: number;
  } = {}
) {
  const { skipInitial = true, debounceMs = 0 } = options;
  const isInitialMount = useRef(true);

  useEffect(() => {
    // Skip reload on initial mount if configured
    if (skipInitial && isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    // Debounce the reload if configured
    if (debounceMs > 0) {
      const timer = setTimeout(() => {
        void reloadFn();
      }, debounceMs);

      return () => clearTimeout(timer);
    }

    // Execute reload immediately
    void reloadFn();
    return;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);
}
