## 2026-03-30 - Palette Init

## 2026-03-30 - Accessible Interactive Elements
**Learning:** Relied on `div`s with `onclick` handlers, limiting keyboard accessibility and screen reader support for key interface elements (like the settings avatar). Without explicit `aria-label`s on select menus and textareas, screen readers lack context. The app was also missing a global focus ring for keyboard navigation.
**Action:** Always use semantic `<button>` elements for interactive click targets. Ensure global `*:focus-visible` styles are defined for keyboard accessibility. Add `aria-label`s to custom inputs and icon-only buttons.

## 2026-03-30 - Disable Async Action Buttons
**Learning:** The send button did not have a visual disabled state during async API calls, allowing double-submission or confusing the user whether the button was clicked.
**Action:** Always add a disabled state visually (`:disabled` pseudo-class dropping opacity/disabling cursor) and functionally (JS `button.disabled = true;` during async calls) for interactive submit buttons.

## 2026-05-28 - Vite Port Binding
**Learning:** When running the `aisha-web` frontend locally for testing via `pnpm dev`, Vite may fall back to alternative ports (like 8080 or 8081) if the default 5173 is occupied, causing Playwright scripts hardcoded to 5173 to fail with connection refused.
**Action:** Always capture the Vite startup logs (e.g., `pnpm dev > vite.log 2>&1 &`) and verify the active port before configuring Playwright navigation URLs.

## 2026-05-28 - Semantic Buttons and Inputs
**Learning:** Found elements acting as buttons constructed as `div`s with `onclick` handlers, and inputs missing ARIA labels, creating accessibility gaps for screen readers and keyboard users.
**Action:** When modifying the `aisha-web` UI, always prioritize accessibility: use semantic `<button>` tags instead of `<div>`s for clickable elements, add explicit `aria-label`s to custom inputs and icon-only buttons, and ensure global `*:focus-visible` styles are maintained for keyboard navigation.
