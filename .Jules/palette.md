## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.
## 2025-05-25 - Interactive Component Keyboard Accessibility
**Learning:** Found that custom interactive components in a monolithic HTML file (like avatar settings triggers, mode tabs, and setting toggles) were built using `<div>` elements without any ARIA attributes or keyboard focus indicators. This meant keyboard users and screen readers couldn't identify or interact with them.
**Action:** Always convert interactive custom components (like tabs or switches) to `<button>` elements to get native keyboard focus and activation behavior. Supplement them with the correct ARIA attributes (`role="tab"`, `aria-selected`, `role="switch"`, `aria-checked`) and explicitly manage those states via inline JavaScript or functions to ensure assistive technologies are kept in sync with the visual state. Additionally, added global `:focus-visible` to surface focus rings without breaking mouse/touch UX.
