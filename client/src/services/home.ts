import type { components } from "@/lib/v1";

export type HomeResource = components["schemas"]["HomeResource"];
export type HomeCollection = components["schemas"]["HomeCollectionPublic"];
export type HomeCollectionWrite = components["schemas"]["HomeCollectionWrite"];

/** Keep empty collections manageable; hide unusable shared collections from readers. */
export function isVisibleCollection(collection: HomeCollection): boolean {
 return collection.can_edit || (collection.resource_keys?.length ?? 0) > 0;
}
