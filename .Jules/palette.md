## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.

## 2026-03-30 - ARIA State Syncing for Toggles
**Learning:** Adding static `aria-checked="true"` attributes to custom HTML toggles (`role="switch"`) creates a critical accessibility issue where the screen reader state drifts from the visual state when the user interacts with it.
**Action:** Always implement or update JavaScript event handlers (like `onclick`) on every instance of custom ARIA components to dynamically sync the ARIA attribute (e.g., `setAttribute("aria-checked", isOn ? "true" : "false")`) with the visual state.
