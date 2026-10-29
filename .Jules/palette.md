## 2024-05-18 - [Screen Reader Support for Live Chat]
**Learning:** Chat applications require explicit `role="log"` on the message container and `aria-live="polite"` to automatically announce incoming messages to screen readers. Status indicators (like "Typing...") also require `aria-live` and `aria-atomic="true"` to read out the full state changes accurately.
**Action:** Always ensure dynamic content containers and status indicators in communication interfaces have appropriate ARIA attributes for live regions.
