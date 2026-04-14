## 2026-04-14 - Icon-only buttons lacking ARIA labels
**Learning:** This app's custom UI heavily relies on icon-only `<button>` elements (e.g., emojis for voice, settings, mic, send) that rely solely on `title` attributes. While `title` provides a tooltip, it is not consistently read by all screen readers, making the interface inaccessible to keyboard and assistive technology users.
**Action:** Ensure all semantic `<button>` elements that use visual-only content (like emojis or SVGs) include an explicit `aria-label` attribute describing their function.
