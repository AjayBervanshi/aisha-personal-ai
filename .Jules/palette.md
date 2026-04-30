## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.

## 2026-03-31 - ARIA Syncing on Custom Toggles
**Learning:** Custom UI toggles (like `.toggle`) that visually update state via classes (e.g., `.on`) without native state management were missing `aria-checked` bindings. This creates an accessibility regression where screen readers hear a switch that never changes state.
**Action:** When retrofitting visual toggles with `role="switch"` and `aria-checked`, always implement dynamic syncing. For visual-only toggles, use inline `onclick` handlers (e.g., `this.setAttribute('aria-checked', this.classList.toggle('on') ? 'true' : 'false')`). For programmatic ones, integrate the syncing directly into the JS function.
