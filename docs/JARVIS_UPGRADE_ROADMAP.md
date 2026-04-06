# 💜 Aisha to J.A.R.V.I.S. Ultimate Upgrade Roadmap

This document outlines an exhaustive, granular plan to enhance Aisha with the OS-level, autonomous, and multi-agent capabilities inspired by the open-source JARVIS project.

## 🏗️ Phase 1: Core Orchestration (The Brain Upgrade)
- [x] **Feature 1.1: Autonomous Sub-Agent Delegation (Done)**
  - *Details:* Agent Task Manager, role-discovery, multi-agent hierarchy (`manage_agents`, `delegate_task`).
- [x] **Feature 1.2: Tool Execution Loop (200 Iterations) (Done)**
  - *Details:* ReAct loop, Thought/Action/Observation paradigm, max iterations, error handling.
- [ ] **Feature 1.3: Knowledge Graph Vault (Memory)**
  - *Details:* SQLite/Supabase entity-relationship graph, automatic fact extraction post-conversation, semantic search injection per message, relationship mappings.
- [ ] **Feature 1.4: Personality Engine**
  - *Details:* Adaptive learning from user feedback, dynamic verbosity/formality/humor scoring, trust-level progression based on message count, channel-specific personality overrides (e.g., Telegram vs Web).

## 💻 Phase 2: OS-Level Action (The Hands)
- [ ] **Feature 2.1: The Local Go Sidecar**
  - *Details:* Lightweight Go binary, JWT-authenticated WebSocket connection, multi-machine support (orchestrate laptop, server, and VM simultaneously).
- [ ] **Feature 2.2: Cross-Platform Desktop Automation**
  - *Details:* Win32 API (UIAutomation, EnumWindows, SendKeys) for Windows, X11 tools (`xdotool`, `wmctrl`) for Linux, macOS (`AXUIElement`).
- [ ] **Feature 2.3: CDP Browser Automation**
  - *Details:* Chrome DevTools Protocol client, session management, 7 browser tools (navigation, interaction, extraction, form filling).
- [ ] **Feature 2.4: Terminal & Filesystem Executor**
  - *Details:* Shell command executor with streaming support, WSL bridge integration (run Windows commands from WSL), filesystem read/write/watch tools.

## 👁️ Phase 3: Continuous Awareness (The Eyes)
- [ ] **Feature 3.1: Desktop Screen Capture & OCR**
  - *Details:* Hybrid OCR (Tesseract.js) + Cloud Vision, 5-10 second interval capture, entity-linked context graph from screen text.
- [ ] **Feature 3.2: Activity & Struggle Detection**
  - *Details:* Application state tracking, activity session inference, detecting repeated errors or stuck states ("struggle detection").
- [ ] **Feature 3.3: Proactive Notifications**
  - *Details:* Desktop overlay widget, proactive Telegram/Discord messages based on detected struggles or context.

## 🎯 Phase 4: Goal Pursuit & Workflows (The Drive)
- [ ] **Feature 4.1: OKR Goal Engine**
  - *Details:* Objective -> Key Result -> Daily Action hierarchy, 0.0-1.0 scoring, morning planning / evening review rhythms, drill-sergeant escalation (pressure -> root cause -> suggest kill).
- [ ] **Feature 4.2: Visual & NLP Workflow Engine**
  - *Details:* ReactFlow visual builder, topological sort execution, 50+ nodes across 5 categories, template expression resolution (`{{var}}`).
- [ ] **Feature 4.3: Workflow Triggers & Self-Healing**
  - *Details:* Cron, webhook, file watch, screen events, clipboard, process polling. Self-heal flow: retry -> LLM analysis -> fixed config -> re-execute.
- [ ] **Feature 4.4: Workflow Auto-Suggestions**
  - *Details:* Detect patterns (app switches, recurring errors, scheduled behavior) and auto-suggest workflow definitions.

## 🎙️ Phase 5: Voice & Audio Streaming
- [ ] **Feature 5.1: Bi-directional Voice WebSocket**
  - *Details:* Binary WebSocket protocol carrying mic audio (WebM) and TTS audio (MP3) concurrently.
- [ ] **Feature 5.2: In-Browser Wake Word**
  - *Details:* `openwakeword` (ONNX) implementation for zero-latency wake word detection ("Aisha").
- [ ] **Feature 5.3: Streaming TTS**
  - *Details:* Edge TTS / ElevenLabs integration with streaming sentence-by-sentence playback.

## 🛡️ Phase 6: Authority & Security
- [ ] **Feature 6.1: Runtime Authority Engine**
  - *Details:* Soft-gate approvals for sensitive actions, multi-channel approval delivery, full audit trail.
- [ ] **Feature 6.2: Consecutive-Approval Learning**
  - *Details:* Aisha learns which actions Ajay always approves and suggests automatic approval rules.
- [ ] **Feature 6.3: Emergency Controls**
  - *Details:* Pause/kill controls for all agent loops and background tasks.

## 👥 Phase 7: Specialist Agent Roster (The Crew)
- [ ] **Feature 7.1: Pre-defined Specialist Roles**
  - *Details:* Implement specific YAML configurations for: Researcher, Coder, Writer, Analyst, Sysadmin, Designer, Planner, Reviewer, Data-Engineer, DevOps, Security.
