## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.
## 2026-04-26 - Async Button Disabled States
**Learning:** In vanilla HTML environments without a framework, asynchronous actions attached to custom buttons often forget to physically disable the interactive element during network requests. Relying purely on visual updates (like text changes or hiding elements) without `disabled = true` allows impatient users to trigger double-submissions. Additionally, when disabling elements, it's vital to pair `element.disabled = true` with a CSS rule like `.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }` and modify existing `:hover`/`:active` states to exclude `:disabled` so users receive clear visual feedback that the action is locked.
**Action:** Always implement a three-part disabled state for async buttons: 1. Set `disabled = true` in JS before the call. 2. Set `disabled = false` in a `finally` block. 3. Add `:disabled` visual CSS rules and exclude them from interactive hover states.

## 2026-04-26 - Keyboard Focus Accessibility
**Learning:** Modern web resets often strip native focus rings or rely on standard browser implementations that clash with custom dark-mode themes, rendering keyboard navigation nearly invisible.
**Action:** Always implement a high-contrast global `*:focus-visible` CSS rule (e.g., `outline: 2px solid var(--accent); outline-offset: 2px;`) aligned with the design system to ensure custom interactive elements are clearly highlighted for keyboard users.
