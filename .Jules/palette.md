## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.
## 2026-06-01 - Asynchronous Feedback UX
**Learning:** Re-evaluating UI state inside the `finally` block of an async operation is crucial. If the UI disabled a button while loading, but the user typed input *during* the loading phase, restoring the button to a hardcoded enabled/disabled state creates a race condition.
**Action:** Always calculate the correct final disabled state based on the current context (e.g., `button.disabled = input.value.trim() === ""`) within the `finally` block, rather than reverting to a naive default.
