## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-04-07 - Semantic Tab Navigation
**Learning:** In the chat interface, the interactive `.mode-pill` elements and the `.setting-row` interactive list items were implemented using generic `<div>` tags with `onclick` handlers, violating accessibility guidelines for keyboard navigation and screen readers. They lacked focusability and explicit ARIA roles indicating their state.
**Action:** Always use semantic native HTML `<button>` elements for clickable controls. When mimicking tabs, add `role="tablist"` to the container and `role="tab"` to the buttons with dynamically updated `aria-selected` attributes. For complex interactive rows, use `<button>` to ensure they participate in the document tab order natively while inheriting standard CSS layout to maintain visual parity.
