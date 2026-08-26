# AI Orchestration Setup Guide

This document explains how Claude Code and ChatGPT are coordinated to work together on OfflineMedia.

## 🔄 Automation System

The system uses GitHub Actions workflows, issue labels, and work log files to coordinate AI-to-AI handoffs and user input.

---

## 📋 Setup Instructions

### Step 1: Create GitHub Labels

Go to: **Repository → Settings → Labels**

Create these labels:

| Label | Color | Description |
|-------|-------|-------------|
| `claude-task` | Blue (#1f77b4) | Work for Claude Code |
| `chatgpt-task` | Green (#2ca02c) | Work for ChatGPT |
| `urgent` | Red (#d62728) | High priority task |
| `ai-coordination` | Purple (#9467bd) | AI handoff coordination |

### Step 2: Enable Actions

Go to: **Repository → Actions**
- Enable all workflows
- Allow actions to create pull requests

### Step 3: Verify Workflows

The following workflows should be active:

- ✅ `.github/workflows/tests.yml` - Run tests
- ✅ `.github/workflows/ai-orchestration.yml` - Coordinate AIs (NEW)

---

## 📝 How to Use

### For Users: Assign Work to Claude Code

1. **Create an Issue**
   - Go to: Repository → Issues → New Issue
   - Click: "AI Task Assignment" template
   - Fill in task details
   - Add label: `claude-task`
   - Submit

2. **GitHub Actions will:**
   - ✅ Detect the issue
   - ✅ Post a comment: "Claude Code has been notified"
   - ✅ Claude Code will automatically read the task

3. **Claude Code will:**
   - ✅ Read the task and work logs
   - ✅ Complete the work
   - ✅ Update `CLAUDE_WORK.txt`
   - ✅ Push changes to the branch

### For Users: Assign Work to ChatGPT

Same process, but use label: `chatgpt-task`

### For Users: Urgent Tasks

Add both `claude-task` and `urgent` labels

---

## 🔄 Workflow: Issue → Claude → ChatGPT → Done

```
1. USER creates GitHub Issue with label "claude-task"
                    ↓
2. GitHub Actions detects issue
                    ↓
3. Workflow posts comment: "Claude has been notified"
                    ↓
4. Claude Code reads issue + work logs
                    ↓
5. Claude completes task, updates CLAUDE_WORK.txt
                    ↓
6. Claude pushes changes to branch
                    ↓
7. GitHub Actions detects CLAUDE_WORK.txt update
                    ↓
8. Workflow posts: "Claude finished. ChatGPT, your turn"
                    ↓
9. ChatGPT reads updated work logs and continues
                    ↓
10. ChatGPT updates CHATGPT_WORK_LOG.txt and pushes
                    ↓
11. Process repeats if more work is needed
```

---

## 📂 Work Log Files

These files are the communication channel between AIs:

### CLAUDE_WORK.txt
- **Created by:** Claude Code (me)
- **Read by:** ChatGPT
- **Contents:**
  - ✅ Work completed
  - ❌ Work pending (by priority)
  - 💡 Suggestions & recommendations
  - 📝 Architecture notes
  - 🔀 Branch status

### CHATGPT_WORK_LOG.txt
- **Created by:** ChatGPT
- **Read by:** Claude Code (me)
- **Contents:**
  - ✅ Work completed
  - ❌ Work pending (by priority)
  - 💡 Strategic decisions
  - 📝 Architecture notes
  - 🔀 Handover instructions

### USER_INPUT.txt (Optional)
- **Created by:** User (via issues)
- **Read by:** Both Claude and ChatGPT
- **Used for:** Explicit user priorities

---

## 🏷️ Label Reference

**Work Assignment Labels:**
- `claude-task` → Assign to Claude Code
- `chatgpt-task` → Assign to ChatGPT

**Priority Labels:**
- `urgent` → High priority (add to any assignment)
- `high-priority` → Important but not blocking

**Status Labels (Added by AIs):**
- `in-progress` → Currently being worked on
- `complete` → Task finished
- `blocked` → Waiting on user feedback or external dependency
- `review-needed` → Ready for human review

---

## 🚀 Example: Assign Work to Claude

### Issue Title:
```
[TASK] Add ComfyUI workflow binding tests
```

### Issue Body:
```
## Task Description
Create comprehensive regression tests for the workflow binding system.
Test both visual and API format workflows.

## Context
This is needed to ensure workflow parameter binding is robust before 
connecting to Portable Colab generation.

## Related to:
- [x] Shared Core
- [x] Testing/CI

## Acceptance Criteria:
- [ ] New test file: tests/test_workflow_binding_advanced.py
- [ ] Tests cover: visual workflows, API workflows, parameter overrides
- [ ] All tests passing (100% green in CI)
- [ ] Work log updated

## Priority:
- [x] 🟡 Medium (Important)

## Assigned AI:
- [x] Claude Code (add `claude-task` label)
```

### What Happens Next:
1. ✅ Issue created with `claude-task` label
2. ✅ GitHub Actions posts: "Claude Code has been notified"
3. ✅ Claude Code reads the issue
4. ✅ Claude implements tests
5. ✅ Claude updates CLAUDE_WORK.txt
6. ✅ Claude pushes to branch
7. ✅ Tests run and pass in CI
8. ✅ ChatGPT sees the update and continues work

---

## 🔍 Monitoring

To see the orchestration in action:

1. **Check Actions tab** → See workflow runs
2. **Check work logs** → See AI progress
3. **Check issue comments** → See orchestration messages
4. **Check branch commits** → See who did what

---

## ⚙️ Troubleshooting

### Workflow not triggering?
- Check: Repository → Actions → Workflows enabled
- Check: Labels are spelled correctly
- Check: Issue is on the right branch

### Work log not updating?
- Make sure the AI pushed changes to the branch
- Check git log for recent commits
- Verify branch is `claude/scan-repo-chatgpt-review-6nljgh`

### Issue not appearing in workflow?
- Refresh: Repository → Actions
- Check workflow runs for errors
- Verify issue has correct label

---

## 📞 Support

If something goes wrong:
1. Check the GitHub Actions logs
2. Review work log files for error messages
3. Check the issue comments for orchestration messages
4. Manually trigger workflow: Repository → Actions → AI Orchestration → Run workflow

---

## 🎯 Best Practices

1. **Be specific in issues** - Clear task descriptions = better results
2. **Use labels consistently** - One label per assignment
3. **Update work logs regularly** - Document progress as you go
4. **Check work logs before starting** - Avoid duplicate work
5. **Keep issues small** - Smaller tasks = faster completion
6. **Link related issues** - Help AIs understand context

---

## 📊 Metrics

You can track AI productivity:
- Commits per AI per week
- Tasks completed per priority level
- Time to task completion
- Test pass rate
- Code quality metrics

---

**Last Updated:** 2026-08-24
**System Version:** 1.0
**Status:** Active and Ready
