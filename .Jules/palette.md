## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.

## 2024-05-01 - Syncing ARIA States on Custom Toggles
**Learning:** For custom toggle switches implemented as visually-styled `<button>` elements, it's not enough to just add the `role="switch"` and initial `aria-checked` attributes. Without dynamic JS logic syncing `aria-checked` with the component's visual state, it becomes a severe accessibility issue where the element lies to screen readers about its actual state.
**Action:** When retrofitting interactive UI elements (like toggle switches) with ARIA state attributes, always implement or update JavaScript event handlers (either inline `onclick` or via specific component state management functions) on every instance to dynamically sync the ARIA attribute (`this.setAttribute('aria-checked', state)`) with the visual class. Avoid using generic disconnected listeners.
