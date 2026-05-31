## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.

## 2024-05-31 - [Adding focus-visible and aria-labels for accessibility]
**Learning:** Found that custom toggle elements and div-based buttons lacked focus-visible states and aria-labels, making keyboard navigation and screen reader usage difficult. Keeping changes strictly scoped to appending aria-labels and CSS `*:focus-visible` ensures accessibility improvements without accidentally breaking semantic HTML/CSS styling regressions when converting div -> button.
**Action:** When improving accessibility on custom UI elements (like toggles or div-buttons), prioritize adding `*:focus-visible` globally for keyboard support, and add explicit `aria-label`s/`role`/`tabindex` rather than attempting full structural HTML overhauls that might break layout constraints.
