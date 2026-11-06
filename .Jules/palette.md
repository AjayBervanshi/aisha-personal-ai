
## 2026-11-06 - Expanding Touch Targets on Custom Switch Rows
**Learning:** When building custom toggle switch rows (like in a settings panel), screen reader users need programmatic association between the visible label and the switch itself (). Additionally, users benefit from having the entire row act as a clickable target for the switch, avoiding frustrating small touch targets.
**Action:** Use a `<button class="setting-row">` to wrap the switch, delegating clicks downwards to the nested `<button class="toggle">`. Apply `onclick="event.stopPropagation()"` to the nested switch to prevent double-firing. Always associate the nested toggle with its visible label using `aria-labelledby`.

## 2023-10-25 - Expanding Touch Targets on Custom Switch Rows
**Learning:** When building custom toggle switch rows (like in a settings panel), screen reader users need programmatic association between the visible label and the switch itself (`aria-labelledby`). Additionally, users benefit from having the entire row act as a clickable target for the switch, avoiding frustrating small touch targets.
**Action:** Use a `<button class="setting-row">` to wrap the switch, delegating clicks downwards to the nested `<button class="toggle">`. Apply `onclick="event.stopPropagation()"` to the nested switch to prevent double-firing. Always associate the nested toggle with its visible label using `aria-labelledby`.
