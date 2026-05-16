## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.
## 2025-05-16 - Inline ARIA State Syncing for Visual Toggles
**Learning:** When dealing with purely visual toggles in a monolithic frontend (like `src/web/index.html`) that lack underlying application state management, it's necessary to sync ARIA states (like `aria-checked`) directly inline. However, nesting `setAttribute` inside `classList.toggle` is an anti-pattern.
**Action:** Use safely sequenced statements inline (e.g., `this.classList.toggle('on'); this.setAttribute('aria-checked', this.classList.contains('on') ? 'true' : 'false')`) to update the visual class and the accessibility attribute reliably.
