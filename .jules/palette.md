## 2024-04-09 - Semantic Buttons for Interactive Elements
**Learning:** In vanilla HTML/CSS environments like `aisha-web` that use custom `<div>` tags for interactive elements (e.g., Mode Pills), screen readers fail to recognize them as selectable tabs/buttons.
**Action:** Convert them to native `<button>` elements, add `font-family: inherit` to prevent system button styling from overriding the app's font, and use appropriate ARIA attributes (`role="tablist"`, `role="tab"`, `aria-selected`).
