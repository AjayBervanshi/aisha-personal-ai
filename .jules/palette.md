## 2024-04-09 - Semantic Buttons for Interactive Elements
**Learning:** In vanilla HTML/CSS environments like `aisha-web` that use custom `<div>` tags for interactive elements (e.g., Mode Pills), screen readers fail to recognize them as selectable tabs/buttons.
**Action:** Convert them to native `<button>` elements, add `font-family: inherit` to prevent system button styling from overriding the app's font, and use appropriate ARIA attributes (`role="tablist"`, `role="tab"`, `aria-selected`).
## 2024-04-10 - Semantic buttons in settings menu
**Learning:** Interactive `<div>` elements with `onclick` handlers in `aisha-web` lack native keyboard accessibility and proper ARIA roles for screen readers. Replacing them with semantic `<button>` tags improves accessibility. However, it's critical to add `font-family: inherit` (along with `color: inherit` and `text-align: left`) to the button's CSS class to prevent the browser's default system button typography from overriding the inherited design.
**Action:** When converting custom interactive elements to native buttons in vanilla HTML/CSS, always ensure typography and alignment are explicitly reset or inherited to maintain consistent styling.
## 2026-04-11 - Temporary UI State Feedback Trap
**Learning:** When using `setTimeout` to temporarily swap UI content (like changing a "Copy" icon to a "✅"), rapid clicks can cause the function to capture the temporary state ("✅") as the `originalIcon`. When the second timeout resolves, it restores the button to "✅" permanently, breaking the UI.
**Action:** Always include a state-guard (e.g., `if (btn.textContent !== "✅")`) before initiating temporary visual feedback loops to ensure idempotency during rapid user interactions.
