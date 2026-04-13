## 2024-04-09 - Semantic Buttons for Interactive Elements
**Learning:** In vanilla HTML/CSS environments like `aisha-web` that use custom `<div>` tags for interactive elements (e.g., Mode Pills), screen readers fail to recognize them as selectable tabs/buttons.
**Action:** Convert them to native `<button>` elements, add `font-family: inherit` to prevent system button styling from overriding the app's font, and use appropriate ARIA attributes (`role="tablist"`, `role="tab"`, `aria-selected`).
## 2024-04-10 - Semantic buttons in settings menu
**Learning:** Interactive `<div>` elements with `onclick` handlers in `aisha-web` lack native keyboard accessibility and proper ARIA roles for screen readers. Replacing them with semantic `<button>` tags improves accessibility. However, it's critical to add `font-family: inherit` (along with `color: inherit` and `text-align: left`) to the button's CSS class to prevent the browser's default system button typography from overriding the inherited design.
**Action:** When converting custom interactive elements to native buttons in vanilla HTML/CSS, always ensure typography and alignment are explicitly reset or inherited to maintain consistent styling.

## 2025-04-13 - Add visual feedback for copy action
**Learning:** Adding visual confirmation (e.g., swapping to a "✅" icon) to clipboard actions significantly improves user confidence. When implementing temporary UI state changes with `setTimeout`, it is critical to include a guard condition (like `btn.textContent !== '✅'`) to prevent rapid subsequent clicks from capturing the temporary state as the "original" state, which would cause the visual feedback to persist permanently.
**Action:** Always include a guard condition when temporarily swapping element states or text, especially on fast-acting interactions like copy-to-clipboard buttons.
