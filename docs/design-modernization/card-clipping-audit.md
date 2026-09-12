# Card boundary audit — 2026-09-08

Apps repeated the Agents clipping condition: an outside box-shadow ring extended
past a card flush with the scroll viewport. The viewport clipped the top and left
outline. This was a second implementation, not the shared Agents card token.

| Surface | Finding and correction |
| --- | --- |
| Apps grid | Draw the outline and focus ring inside the card with `ring-inset`. |
| Agents grid | Already uses the corrected shared inset card surface. |
| Forms grid | Uses the shared Card border; no outside outline correction needed. |
| Solution Detail entity cards | Replace the older outside ring and upward hover translation with the standard border, radius and color transition; keep focus inside the boundary. |
| Image file preview | Use a real border inside the max-sized image box. |

The source audit searched page and component card treatments for outside rings,
shadows and hover translations. Remaining matches were padded callouts, swatches,
sticky controls and floating surfaces rather than flush list cards. This audit
addresses the identified outline/translation clipping condition; it does not
claim every possible overflow interaction was browser-tested.

Parent browser review confirmed complete top/left Apps card edges at 1440px and
390px. Forms and Agents were checked at the source contract. Solution Detail and
image preview corrections were source-reviewed, not separately screenshot-tested.
Applications tests passed (11), scoped lint passed and TypeScript passed.

Keep card outlines and keyboard focus inside scroll boundaries. Avoid upward
hover translations on cards at the first row unless the viewport reserves space
for them. Review actual card edges, not only document overflow measurements.
