## 2026-04-14 - Icon-only buttons lacking ARIA labels
**Learning:** This app's custom UI heavily relies on icon-only `<button>` elements (e.g., emojis for voice, settings, mic, send) that rely solely on `title` attributes. While `title` provides a tooltip, it is not consistently read by all screen readers, making the interface inaccessible to keyboard and assistive technology users.
**Action:** Ensure all semantic `<button>` elements that use visual-only content (like emojis or SVGs) include an explicit `aria-label` attribute describing their function.
## 2024-04-09 - Semantic Buttons for Interactive Elements
**Learning:** In vanilla HTML/CSS environments like `aisha-web` that use custom `<div>` tags for interactive elements (e.g., Mode Pills), screen readers fail to recognize them as selectable tabs/buttons.
**Action:** Convert them to native `<button>` elements, add `font-family: inherit` to prevent system button styling from overriding the app's font, and use appropriate ARIA attributes (`role="tablist"`, `role="tab"`, `aria-selected`).
## 2024-04-10 - Semantic buttons in settings menu
**Learning:** Interactive `<div>` elements with `onclick` handlers in `aisha-web` lack native keyboard accessibility and proper ARIA roles for screen readers. Replacing them with semantic `<button>` tags improves accessibility. However, it's critical to add `font-family: inherit` (along with `color: inherit` and `text-align: left`) to the button's CSS class to prevent the browser's default system button typography from overriding the inherited design.
**Action:** When converting custom interactive elements to native buttons in vanilla HTML/CSS, always ensure typography and alignment are explicitly reset or inherited to maintain consistent styling.
## 2026-04-11 - Temporary UI State Feedback Trap
**Learning:** When using `setTimeout` to temporarily swap UI content (like changing a "Copy" icon to a "✅"), rapid clicks can cause the function to capture the temporary state ("✅") as the `originalIcon`. When the second timeout resolves, it restores the button to "✅" permanently, breaking the UI.
**Action:** Always include a state-guard (e.g., `if (btn.textContent !== "✅")`) before initiating temporary visual feedback loops to ensure idempotency during rapid user interactions.
## 2026-05-29 - Mode pills lacked semantic accessibility
**Learning:** In the `aisha-web` frontend, interactive mode selection pills were implemented as `<div>` elements relying on `onclick` handlers, without keyboard focus (`tabindex`) or ARIA roles, making them inaccessible to keyboard and screen-reader users.
**Action:** Replaced the `<div>` pills with native `<button>` tags, added `role="tablist"` to the parent container and `role="tab"` to the buttons. Ensured custom styling was preserved by adding `font-family: inherit; outline: none;` and improved keyboard accessibility by adding a `:focus-visible` outline.
