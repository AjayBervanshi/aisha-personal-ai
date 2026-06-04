## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.

## 2026-06-04 - Global Focus Visible
**Learning:** The UI lacked keyboard accessibility because custom buttons (like `.icon-btn`, `.quick-btn`) stripped native outlines or only relied on `:hover`. Adding a global `*:focus-visible` rule provides a robust, low-effort safety net for keyboard navigation across the entire monolithic app.
**Action:** Implement global `*:focus-visible` using design system tokens (`--accent`) to ensure baseline accessibility for all interactive elements, especially icon-only buttons.
