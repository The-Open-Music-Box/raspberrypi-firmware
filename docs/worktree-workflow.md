---
title: "Worktree Workflow"
status: deprecated
category: guide
last_reviewed: 2026-02-09
review_cycle: 12months
---

# Git Worktree Workflow for Multiple Claude Sessions

## Problem

When working with multiple Claude Code sessions on the same repository, conflicts can arise:
- Branch switching in one session affects all others
- Staged changes can get mixed up
- Concurrent work becomes difficult

## Solution: Git Worktrees

Git worktrees allow multiple branches to be checked out simultaneously in different directories, while sharing the same `.git` repository.

## Quick Start

### 1. Create a worktree for a new issue

```bash
./scripts/worktree.sh create 75 feat "audio-enhancement"
```

This creates:
- A new branch: `feat/issue-75-audio-enhancement`
- A new directory: `../rpi-firmware-wt-75`

### 2. Open the worktree in Claude Code

```bash
cd ../rpi-firmware-wt-75
# Or open directly in Claude Code
claude ../rpi-firmware-wt-75
```

### 3. Work independently

Each worktree is completely independent:
- Different branch
- Different working directory
- Different staging area
- But shares the same Git history

### 4. When done, clean up

```bash
./scripts/worktree.sh remove 75
```

## Complete Workflow Example

### Scenario: Working on 3 issues simultaneously with 3 Claude sessions

```bash
# Terminal 1: Create worktree for feature work
cd ~/github/theopenmusicbox/rpi-firmware
./scripts/worktree.sh create 75 feat "audio-enhancement"
claude ../rpi-firmware-wt-75

# Terminal 2: Create worktree for bug fix
cd ~/github/theopenmusicbox/rpi-firmware
./scripts/worktree.sh create 76 fix "memory-leak"
claude ../rpi-firmware-wt-76

# Terminal 3: Create worktree for refactoring
cd ~/github/theopenmusicbox/rpi-firmware
./scripts/worktree.sh create 77 refactor "playlist-service"
claude ../rpi-firmware-wt-77
```

Now each Claude session works in its own directory without conflicts!

## Command Reference

### Create a new worktree

```bash
./scripts/worktree.sh create <issue-number> <type> <description>
```

**Types:** `feat`, `fix`, `refactor`, `chore`, `docs`, `test`

**Example:**
```bash
./scripts/worktree.sh create 75 feat "audio-enhancement"
```

### List all worktrees

```bash
./scripts/worktree.sh list
```

Output:
```
~/github/theopenmusicbox/rpi-firmware         f44e4fcd7 [develop]
~/github/theopenmusicbox/rpi-firmware-wt-75  a1b2c3d4e [feat/issue-75-audio-enhancement]
~/github/theopenmusicbox/rpi-firmware-wt-76  e5f6g7h8i [fix/issue-76-memory-leak]
```

### Switch to a worktree

```bash
cd $(./scripts/worktree.sh switch 75)
```

### Show status of all worktrees

```bash
./scripts/worktree.sh status
```

This shows which worktrees have uncommitted changes.

### Remove a specific worktree

```bash
./scripts/worktree.sh remove 75
```

The script will warn you if there are uncommitted changes.

### Clean all worktrees

```bash
./scripts/worktree.sh clean
```

This removes all worktrees except the main repository (with confirmation).

## Best Practices

### 1. One worktree per issue

Create a dedicated worktree for each GitHub issue you're working on:

```bash
./scripts/worktree.sh create 75 feat "description"
```

### 2. Name your terminal/Claude sessions

Use clear terminal titles or Claude session names to avoid confusion:
- "Claude - Issue #75 - Audio Enhancement"
- "Claude - Issue #76 - Memory Leak Fix"

### 3. Check status regularly

Before removing a worktree, check its status:

```bash
./scripts/worktree.sh status
```

### 4. Clean up when done

After merging a PR, remove the corresponding worktree:

```bash
# After merging PR for issue #75
./scripts/worktree.sh remove 75
```

### 5. Keep main repo clean

Use the main repository (`rpi-firmware/`) only for:
- Pulling updates
- Creating new worktrees
- Reviewing overall project state

Don't do active development there—use worktrees instead.

## Integration with Existing Workflow

Your existing workflow (from CLAUDE.md) works perfectly with worktrees:

### Standard workflow:

1. **Verify/create GitHub issue**
   ```bash
   gh issue view 75
   # or create if needed
   ```

2. **Create worktree and branch** (instead of just creating a branch)
   ```bash
   ./scripts/worktree.sh create 75 feat "audio-enhancement"
   cd ../rpi-firmware-wt-75
   ```

3. **Work on the task with Claude**
   - Open Claude in the worktree directory
   - Develop step by step with commits
   - Todo list tracking

4. **Create PR when complete**
   ```bash
   git push github feat/issue-75-audio-enhancement
   gh pr create
   ```

5. **After PR is merged**
   ```bash
   # In main repo
   cd ~/github/theopenmusicbox/rpi-firmware
   git checkout develop
   git pull github develop

   # Remove the worktree
   ./scripts/worktree.sh remove 75
   ```

6. **Rebase other worktrees**
   ```bash
   # For each remaining worktree
   cd ../rpi-firmware-wt-76
   git fetch github
   git rebase develop
   ```

## Troubleshooting

### "Worktree already exists"

If you see this error, list existing worktrees:

```bash
./scripts/worktree.sh list
```

Then either remove the existing one or use a different issue number.

### "Branch already exists"

The script will checkout the existing branch. If you want a fresh start:

```bash
# Delete the branch first
git branch -D feat/issue-75-audio-enhancement
# Then create the worktree
./scripts/worktree.sh create 75 feat "audio-enhancement"
```

### Can't remove worktree with uncommitted changes

The script will warn you. Either:
- Commit the changes
- Stash them: `git stash`
- Force remove: `git worktree remove --force ../rpi-firmware-wt-75`

### Worktree directory structure

All worktrees are created in the parent directory:

```
github/
└── theopenmusicbox/
    ├── rpi-firmware/              # Main repo
    ├── rpi-firmware-wt-75/        # Worktree for issue #75
    ├── rpi-firmware-wt-76/        # Worktree for issue #76
    └── rpi-firmware-wt-77/        # Worktree for issue #77
```

## Advantages of This Approach

1. **Isolation:** Each Claude session has its own workspace
2. **Speed:** No need to switch branches or stash changes
3. **Safety:** Can't accidentally affect other sessions
4. **Efficiency:** Shared Git history (no duplication)
5. **Clarity:** Clear separation of work by issue number
6. **Parallel work:** Multiple Claude sessions can work simultaneously

## Additional Resources

- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
- [Git Worktree Tutorial](https://git-scm.com/book/en/v2/Git-Tools-Advanced-Merging)
