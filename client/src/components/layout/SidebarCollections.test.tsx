import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { SidebarCollections } from "./SidebarCollections";

const query = vi.hoisted(() => ({ collections: [] as Array<{ id: string; name: string; icon: string; can_edit: boolean; resource_keys: string[] }> }));
vi.mock("@/lib/api-client", () => ({ $api: { useQuery: () => ({ data: query }) } }));

describe("SidebarCollections", () => {
 it("omits the entire section when no collections exist", () => {
  query.collections = [];
  renderWithProviders(<SidebarCollections isCollapsed={false} />);
  expect(screen.queryByText("Collections")).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "New collection" })).not.toBeInTheDocument();
 });
 it("keeps empty collections manageable but hides empty shared collections from readers", () => {
  query.collections = [
   { id: "mine", name: "My empty collection", icon: "folder", can_edit: true, resource_keys: [] },
   { id: "hidden", name: "Empty shared collection", icon: "folder", can_edit: false, resource_keys: [] },
   { id: "visible", name: "Useful shared collection", icon: "folder", can_edit: false, resource_keys: ["app:1"] },
  ];
  renderWithProviders(<SidebarCollections isCollapsed={false} />);
  expect(screen.getByRole("link", { name: "My empty collection" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Useful shared collection" })).toBeInTheDocument();
  expect(screen.queryByText("Empty shared collection")).not.toBeInTheDocument();
 });
});
