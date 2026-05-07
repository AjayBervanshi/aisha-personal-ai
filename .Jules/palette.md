## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.

## 2026-05-07 - Toggle Switch Accessibility
**Learning:** Purely visual toggle switches built with `<button>` and CSS classes lack semantics for screen readers, leading to confusing interactions where the state is unknown. Without dynamic syncing, hardcoding ARIA states is an anti-pattern.
**Action:** Always add `role="switch"` and `aria-checked` to custom toggle components, and explicitly sync the `aria-checked` attribute in the corresponding JavaScript event handler (or inline via sequenced statements) whenever the visual state changes.
