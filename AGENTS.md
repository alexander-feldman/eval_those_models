# Agent workflow

## Worktree isolation is required for coding

Every Codex session that will change files must do its work in a dedicated Git
worktree. Read-only investigation, planning, and review may use the current
checkout, but create or select the worktree before the first edit, generated
file, dependency installation, formatter run, or other command that can modify
the repository.

At the start of a coding task:

1. Identify the Git root, current branch/status, default remote branch, and
   existing worktrees. This repository's default branch is `main`.
2. If the session is already in a worktree dedicated to this task, use it. If it
   is detached, create a task branch there before committing.
3. Otherwise, create a new branch and worktree for the task. Use a descriptive
   `codex/<short-task-slug>` branch and a unique sibling path such as
   `../worktrees/<short-task-slug>`. Base it on the latest available
   `origin/main`; fetch first when network access is available.
4. Run every subsequent edit, build, and test from that worktree. Explicitly
   set the working directory for commands rather than assuming the shell moved.

Equivalent setup commands are:

```bash
git fetch origin main
git worktree add -b codex/<short-task-slug> ../worktrees/<short-task-slug> origin/main
```

If either the branch or path already exists, choose a unique suffix. Never
delete, reset, stash, commit, or otherwise alter another checkout's uncommitted
work to make worktree creation succeed. Do not include unrelated local changes
in the task branch. If the requested work depends on uncommitted changes that
cannot safely be reproduced in the new worktree, stop and explain the blocker.

## Delivery through a pull request

The completed result of every coding task must be a reviewable pull request to
`main`, not a direct change to `main` and not only an uncommitted local diff.

Before opening the pull request:

1. Review the complete diff and remove unrelated changes.
2. Run the repository's relevant tests, linters, and formatters. Record any
   checks that could not be run and why.
3. Commit the finished work on the task branch with a focused message.
4. Push the task branch to `origin`.
5. Open a GitHub pull request targeting `main`. Give it a clear title and a body
   containing a concise summary and the exact validation performed.

Use `gh pr create --base main --head codex/<short-task-slug>` when GitHub CLI is
available. Creating the branch, pushing it, and opening the pull request are
part of the requested workflow and do not require a separate confirmation. Do
not merge the pull request; leave that decision to the user.

At handoff, report the pull request URL, branch name, worktree path, test
results, and any remaining risks or follow-ups. Keep the worktree until the pull
request is merged or the user asks for cleanup, and never remove another
session's worktree.
