---
name: AI Task Assignment
about: Assign work to Claude Code or ChatGPT
title: "[TASK] Brief description of work"
labels: ["claude-task"]
---

## Task Description

**What needs to be done?**
<!-- Describe the task clearly and concisely -->

## Context

**Why is this task needed?**
<!-- Provide context about why this work is important -->

**Related to:**
- [ ] Mainload (Windows application)
- [ ] Portable (Google Colab)
- [ ] Shared Core
- [ ] Testing/CI
- [ ] Documentation

## Acceptance Criteria

- [ ] Task completed
- [ ] Tests passing
- [ ] Work log updated
- [ ] Changes documented

## Priority

**Level:** 
- [ ] 🔴 High (Blocking)
- [ ] 🟡 Medium (Important)
- [ ] 🟢 Low (Nice-to-have)

## Assigned AI

**Assign to:**
- [ ] Claude Code (add `claude-task` label)
- [ ] ChatGPT (add `chatgpt-task` label)
- [ ] Both (sequential)

## Notes

<!-- Any additional notes or context -->

---

**Workflow:**
1. Issue is created with appropriate label
2. GitHub Actions notifies the assigned AI
3. AI updates its work log when starting
4. AI comments when complete
5. Next AI in sequence continues if needed
