## 2024-05-18 - Screen Reader Support for Live Chat
**Learning:** Chat applications require explicit `role="log"` on the message container and `aria-live="polite"` to automatically announce incoming messages to screen readers. Status indicators (like "Typing...") also require `aria-live` and `aria-atomic="true"` to read out the full state changes accurately.
**Action:** Always ensure dynamic content containers and status indicators in communication interfaces have appropriate ARIA attributes for live regions.

## 2026-10-30 - Disable Send Button by Default
**Learning:** Users often don't realize when they have typed something empty. Disabling the send button dynamically when the input is empty gives immediate visual feedback. Contextual tooltips help discoverability of shortcuts.
**Action:** Implemented dynamic disabling of the send button based on text input and added contextual tooltips.

## 2024-10-31 - Screen Reader Noise from Chat Avatars & Dynamic Button States
**Learning:** Screen readers announce visual-only emojis like "purple heart" repeatedly in chat logs unless explicitly hidden. Also, buttons that toggle persistent states (like recording voice) need dynamic updates to their `aria-label` and `title` to reflect the *next* available action, not just the generic feature name.
**Action:** Added `aria-hidden="true"` to decorative message avatars and implemented dynamic `aria-label`/`title` updates for the microphone toggle button.
## 2023-11-02 - Keyboard Inaccessible Hover Actions
**Learning:** Using `display: none` for hover-only message actions completely removes them from the DOM tab order, making them inaccessible to keyboard/screen-reader users. Additionally, changing to `display: flex` on hover causes layout shifts.
**Action:** Use `opacity: 0` with `pointer-events: none` by default, and switch to `opacity: 1` and `pointer-events: auto` on `:hover` and `:focus-within` to maintain tab sequence and visual stability.

## 2024-11-05 - Missing Keyboard Focus Trap in Slide-out Panels
**Learning:** Custom slide-out panels with `aria-modal="true"` require explicit focus traps. Without them, keyboard users (using Tab) and screen readers can easily navigate out of the modal and interact with the background content, even though it appears visually hidden or disabled.
**Action:** Implemented a focus trap in `toggleSettings` using a keydown listener that traps the `Tab` key (and handles `Shift+Tab`) strictly within the modal's focusable elements, and ensures the modal closes on `Escape`.
