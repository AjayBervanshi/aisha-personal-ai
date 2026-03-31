## 2026-03-30 - Palette Init

## 2026-03-30 - Interactive element accessibility improvements
**Learning:** Using `<div>` elements with `onclick` handlers (like `.avatar`, `.mode-pill`) is a common anti-pattern that breaks keyboard navigation (tabbing) and screen reader support.
**Action:** Always convert interactive pseudo-buttons to semantic `<button>` elements, reset their default styles (`border: none; font-family: inherit;`), and ensure they have visible focus rings (`:focus-visible`) and proper `aria-label`s.
