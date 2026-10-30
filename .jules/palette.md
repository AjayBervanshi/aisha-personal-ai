## 2024-05-18 - Screen Reader Support for Live Chat
**Learning:** Chat applications require explicit `role="log"` on the message container and `aria-live="polite"` to automatically announce incoming messages to screen readers. Status indicators (like "Typing...") also require `aria-live` and `aria-atomic="true"` to read out the full state changes accurately.
**Action:** Always ensure dynamic content containers and status indicators in communication interfaces have appropriate ARIA attributes for live regions.

## 2026-10-30 - Disable Send Button by Default
**Learning:** Users often don't realize when they have typed something empty. Disabling the send button dynamically when the input is empty gives immediate visual feedback. Contextual tooltips help discoverability of shortcuts.
**Action:** Implemented dynamic disabling of the send button based on text input and added contextual tooltips.
