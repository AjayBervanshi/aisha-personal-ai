## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.

## 2026-05-19 - ARIA Switch Toggles
**Learning:** Found pure visual UI toggles (`<button class="toggle">`) that lacked semantics and keyboard support, making them invisible and unusable to screen readers. Relying solely on `class="on"` to indicate state is an accessibility anti-pattern. Inline toggling of class and ARIA state must be carefully sequenced to avoid nesting `.toggle()` inside `.setAttribute()`.
**Action:** Always add `role="switch"` and `aria-checked` to custom visual toggles. Sync the ARIA state accurately inline using safely sequenced statements (`onclick="this.classList.toggle('on'); this.setAttribute('aria-checked', this.classList.contains('on') ? 'true' : 'false')"`). Include global `*:focus-visible` to support keyboard navigation.
