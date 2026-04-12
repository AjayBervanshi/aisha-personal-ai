## 2024-04-09 - Semantic Buttons for Interactive Elements
**Learning:** In vanilla HTML/CSS environments like `aisha-web` that use custom `<div>` tags for interactive elements (e.g., Mode Pills), screen readers fail to recognize them as selectable tabs/buttons.
**Action:** Convert them to native `<button>` elements, add `font-family: inherit` to prevent system button styling from overriding the app's font, and use appropriate ARIA attributes (`role="tablist"`, `role="tab"`, `aria-selected`).
## 2024-04-10 - Semantic buttons in settings menu
**Learning:** Interactive `<div>` elements with `onclick` handlers in `aisha-web` lack native keyboard accessibility and proper ARIA roles for screen readers. Replacing them with semantic `<button>` tags improves accessibility. However, it's critical to add `font-family: inherit` (along with `color: inherit` and `text-align: left`) to the button's CSS class to prevent the browser's default system button typography from overriding the inherited design.
**Action:** When converting custom interactive elements to native buttons in vanilla HTML/CSS, always ensure typography and alignment are explicitly reset or inherited to maintain consistent styling.
## 2024-05-18 - Visual Feedback for Copy Button
**Learning:** When implementing temporary UI state changes (e.g., swapping a button's text to a '✅' checkmark for feedback), subsequent rapid clicks can capture the temporary '✅' state as the original text, causing the visual feedback to persist permanently when the timeout completes.
**Action:** Always include a guard condition (e.g., `btn.textContent !== '✅'`) to prevent rapid consecutive clicks from executing the state change logic while the element is already in the feedback state.
