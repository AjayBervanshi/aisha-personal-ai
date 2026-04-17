## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.
## 2026-04-17 - ARIA State Syncing
**Learning:** Adding ARIA state attributes (like `aria-checked` on `role="switch"`) requires synchronizing that attribute dynamically via JavaScript whenever the component's state changes. If you only add the initial HTML attribute, screen readers will receive static, incorrect information when the user interacts with the element.
**Action:** Always ensure that when retrofitting interactive elements with ARIA state attributes, every instance of that component has an active JavaScript event handler that dynamically updates the ARIA attribute to mirror the visual/functional state.
