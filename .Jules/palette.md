## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-31 - Mode Pills Accessibility
**Learning:** The chat modes selection UI (`.mode-strip`) used `<div>` elements with `onclick` handlers, rendering them inaccessible to screen readers and keyboard navigation (missing `role="tab"`, `aria-selected`, and proper `tablist` container). Furthermore, changing the pills to semantic `<button>` elements revealed that `font-family: inherit` must be explicitly set on the `.mode-pill` class to prevent buttons from defaulting to the browser's system UI font, which breaks the visual design consistency.
**Action:** When converting custom interactive `<div>` elements to semantic `<button>`s, always remember to add `font-family: inherit` to preserve intended typography. Use standard ARIA roles (`tablist`, `tab`) for group selection components.
