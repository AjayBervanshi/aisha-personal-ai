## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.

## 2026-03-30 - Visual Feedback for Clipboard Actions
**Learning:** The copy button lacked visual feedback, leaving users unsure if the action succeeded. When implementing temporary UI state changes (like swapping text/icons using `setTimeout`), rapid subsequent clicks can capture the temporary state (e.g., '✅') as the 'original' state, causing the visual feedback to persist permanently.
**Action:** Always include a guard condition (e.g., `btn.textContent !== '✅'`) when implementing temporary visual states to prevent rapid clicks from corrupting the captured original state.
