# 💜 Aisha to J.A.R.V.I.S. Upgrade Roadmap

This document outlines the systematic plan to enhance Aisha with the OS-level, autonomous, and multi-agent capabilities inspired by the open-source JARVIS project, while maintaining her core identity as a personal AI soulmate.

## 🏗️ Phase 1: Core Orchestration (The Brain Upgrade)
To support complex tasks, Aisha's brain must evolve beyond single-prompt responses.

- [ ] **Feature 1.1: Autonomous Sub-Agent Delegation (In Progress)**
  - **What:** An Agent Task Manager that allows Aisha to spin up "specialist" agents (e.g., Researcher, Analyst).
  - **Autonomy:** Aisha decides *when* to wake them up based on the user's request complexity.
- [ ] **Feature 1.2: Tool Execution Loop (200 Iterations)**
  - **What:** Give Aisha the ability to execute tools, read the result, and decide the next step autonomously in a loop until the task is complete.
- [ ] **Feature 1.3: Knowledge Graph Vault**
  - **What:** Upgrade Supabase memory to an entity-relationship graph for deeper, structured context injection.

## 💻 Phase 2: OS-Level Action (The Hands)
Giving Aisha the ability to affect the real world.

- [ ] **Feature 2.1: The Local Python Sidecar**
  - **What:** A lightweight, secure local script that connects to Aisha's cloud brain via WebSocket.
- [ ] **Feature 2.2: Local Computer Control**
  - **What:** Adding tools to the sidecar for terminal execution, file system management, and desktop manipulation.
- [ ] **Feature 2.3: CDP Browser Automation**
  - **What:** Giving Aisha a headless browser to surf the web, scrape data, and fill out forms automatically.

## 👁️ Phase 3: Continuous Awareness (The Eyes)
Allowing Aisha to see what Ajay is doing without being explicitly spoken to.

- [ ] **Feature 3.1: Periodic Screen Capture & OCR**
  - **What:** The sidecar takes screenshots every 10 seconds, reads the text, and sends context to Aisha.
- [ ] **Feature 3.2: Activity Session Inference**
  - **What:** Aisha automatically detects what Ajay is doing (e.g., "Coding," "Watching YouTube," "Struggling with a bug").
- [ ] **Feature 3.3: Proactive Suggestions**
  - **What:** Aisha reaches out on Telegram *first* when she sees Ajay needs help.

## 🎯 Phase 4: Goal Pursuit & Workflows (The Drive)
- [ ] **Feature 4.1: OKR Goal Engine**
  - **What:** Translating goals into objectives, key results, and daily actions tracked via awareness.
- [ ] **Feature 4.2: Visual/NLP Workflow Engine**
  - **What:** Allowing Aisha to run CRON jobs, webhooks, and complex multi-step automated routines in the background.

---
*Note: Each feature will be implemented in a dedicated Pull Request to ensure stability and proper integration.*
