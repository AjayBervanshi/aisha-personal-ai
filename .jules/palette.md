## 2026-04-05 - Native Interactive Elements for A11y
**Learning:** Using `<div>` with `onclick` for interactive elements like tabs misses out on out-of-the-box keyboard accessibility (focus/enter) and screen reader context. Semantics matter immensely for accessible UI components.
**Action:** Always prefer native interactive elements like `<button>` with appropriate ARIA roles (e.g., `role="tab"`) and states (`aria-selected`) instead of relying purely on visual CSS classes and custom JS handlers.
