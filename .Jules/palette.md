## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.

## 2024-05-18 - Messaging Input Empty State Feedback
**Learning:** Users can become confused when a message action button is visually enabled but functionally inactive because the input field is empty. Relying on function-level guards (`if (!text) return;`) prevents errors but fails to communicate system state to the user visually.
**Action:** Always visually disable message submission buttons using the `disabled` attribute when the corresponding input field is empty or when a network request is currently active. Utilize `oninput` handlers to dynamically toggle the disabled state based on the input text content.
