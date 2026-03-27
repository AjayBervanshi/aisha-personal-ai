# Aisha Chaos Stress Report (Random Mixed + Edge + Invalid)

Date: 2026-03-27  
Run ID: `chaos_20260327_051258`  
Raw Record: `tests/records/telegram_chaos_20260327_051258.json`

## 1. Skills & Plugins Used

### Skills used in this run
- `superpowers:brainstorming` (designing chaos categories and test strategy)
- `superpowers:dispatching-parallel-agents` (attempted planner/reviewer agent split; failed due disk)
- `superpowers:systematic-debugging` (root-cause analysis of failure patterns)
- `superpowers:verification-before-completion` (fresh command evidence before claims)

### Requested but unavailable in this environment
- `pr-review-toolkit:silent-failure-hunter`
- `webapp-testing` (plugin name requested; not available as installable tool here)
- `coderabbit:code-review`
- `ln-1000-pipeline-orchestrator`
- `ln-500-story-quality-gate`
- `owasp-security` (as plugin)
- `security-guidance` (as plugin)

### Execution note
- Parallel sub-agents were triggered but errored with OS disk issue (`os error 112`, no space on `C:`). Main agent continued the campaign directly.

## 2. Random Tasks Generated

Mandatory categories covered (2 each):
- Expected: `E004`, `E002`
- Unexpected: `U002`, `U006`
- Mixed: `M004`, `M002`
- Edge: `X005`, `X002`
- Invalid/Corrupted: `I005`, `I004`

## 3. Execution Results

### Aggregate
- Tasks tested: `10`
- Behavior OK: `2`
- Behavior fail: `8`
- Success rate: `20%`
- Average score: `48/100`
- Voice-note-only replies: `7`
- Suspected reply mismatch/bleed: `2`

### Per-task highlights
- Strong:
  - `I005` (corrupted bytes) handled gracefully with clarification.
  - `E002` produced substantial response (but semantic mismatch to asked task).
- Weak:
  - `E004`, `M004`, `M002`, `X005`, `X002`, `I004`: returned mostly voice-note metadata (`0:xx • xx KB`) instead of text output.
  - `U002`: out-of-scope task got repeated stale voice-note metadata.
  - `U006`: capability boundary answer was safe, but strict auto-classifier marked fail.

## 4. Failures & Weaknesses

1. **Critical: response-mode instability**
- Bot frequently emits voice-note-only placeholders instead of actual text answers.
- This breaks expected, mixed, edge, and invalid categories simultaneously.

2. **Critical: reply mapping / bleed**
- Same prior voice response repeated across different prompts.
- Indicates turn-correlation weakness (reply attached to wrong query window).

3. **Constraint-following under stress is unreliable**
- Edge instructions (format/one-line/bullet constraints) frequently not satisfied due mode bleed.

4. **Classifier sensitivity gap (tester-side)**
- Some safe refusals were marked fail by strict phrase matching.
- Evaluation pipeline needs semantic refusal detection, not just keyword exactness.

## 5. Adaptability Analysis

### Did Aisha understand unknown tasks?
- Partially. Safe boundary behavior appeared on `U006`, but consistency was poor.

### Can Aisha generalize across mixed tasks?
- Weak in this run due output-mode instability (voice-note metadata replacing content).

### Can Aisha recover from confusion?
- Limited. Once the voice-mode/bleed state started, multiple subsequent tasks were degraded.

### Adaptability Score
- **`41/100` (Low-Moderate)**
- Reason: isolated strong responses exist, but under random mixed stress, mode consistency collapses.

## 6. Improvement Plan

### P0 (Immediate)
1. Enforce deterministic response mode per message
- Hard lock `text-only` in command router for test and critical ops flows.
- Confirm mode state before composing response.

2. Add message correlation IDs
- Every incoming Telegram event gets `request_id`.
- Outgoing response must match active `request_id`; drop stale async emissions.

3. Add anti-bleed queue guard
- Per-chat single-flight processing with timeout + explicit completion.

### P1 (High)
4. Add fallback decomposition logic
- If voice generation fails, always fallback to text answer (never metadata-only).

5. Strengthen out-of-scope refusal quality
- Include clear boundary + next best alternative action.

6. Add structured observability
- Log mode (`text/voice`), request_id, handler name, provider used, completion status.

### P2 (Medium)
7. Improve stress-test evaluator
- Semantic classifier for safe refusal and intent match.
- Distinguish “safe refusal pass” from “strict template pass.”

## 7. Final System Robustness Score

- **Robustness Score: `44/100`**
- Not ready for autonomous real-world random workload yet.
- Primary blocker: **mode/turn consistency failure**, not core language intelligence.

## 8. Self-Validation

- Diversity check: PASS (all 5 mandatory categories covered)
- Randomness check: PASS (mixed category order and domain variety)
- Edge/invalid check: PASS (format constraints + malformed inputs included)
- Blind spots remaining:
  - Long-session memory drift testing (>30 turns)
  - Latency distribution measurement (p50/p95)
  - Multi-language refusal consistency under rapid-fire prompts

