## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.

## 2026-03-31 - ARIA states for toggle switches
**Learning:** Custom UI components styled as toggles (switches) lacked the `aria-checked` and `role="switch"` attributes, meaning screen readers would just announce them as a "button" without identifying their state (on/off).
**Action:** When implementing custom visual switches, always add `role="switch"`, an initial `aria-checked` state, and an inline or handler function that syncs the `aria-checked` attribute securely with the visual class toggling logic (`this.classList.toggle('on'); this.setAttribute('aria-checked', ...)`).
