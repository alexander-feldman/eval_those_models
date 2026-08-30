---
name: git-worktree-cleanup
description: Audit and safely clean Git repositories with multiple worktrees, stale branches, confusing uncommitted state, and merged pull requests. Use when asked to inspect Git state, organize worktrees, or remove completed task branches; do not use for ordinary feature-branch commits or active development.
---

# Git Worktree Cleanup

Produce a trustworthy map of the repository before changing it. Treat cleanup as a separate, explicitly authorized phase.

## Audit

1. Read applicable `AGENTS.md` instructions. Identify the Git root, current branch and status, default remote branch, remotes, existing worktrees, local branches with upstreams, and stashes.
2. Refresh remote refs with `git fetch --prune` when network access is available. Report if the fetch cannot be performed; do not present stale refs as current.
3. Run `git status --short --branch` in every worktree. Use explicit worktree paths from `git worktree list --porcelain`; do not assume the current checkout represents the others.
4. When GitHub CLI is available, list open and recently merged pull requests and associate their head branches with worktrees. Treat `MERGEABLE` as different from `MERGED`.
5. Classify each item as active, clean and merged, stale metadata, uncommitted work, or uncertain. Identify the default branch and root checkout separately because neither should be removed as task cleanup.

If a checkout looks dirty because its `HEAD` or index is stale, verify its working-tree content before calling it disposable. Compare tracked files byte-for-byte with the relevant committed tree and check whether every untracked, non-ignored file exists in that tree. A matching directory listing alone is insufficient.

Present the audit before mutation. Include worktree path, branch, dirty/clean state, ahead/behind state, pull-request state, and a recommended action.

## Safety gates

Remove a task worktree or branch only when all applicable conditions hold:

- The worktree has no staged, unstaged, or untracked non-ignored changes.
- `git merge-base --is-ancestor <branch> <default-remote-branch>` succeeds.
- Its pull request is confirmed merged when pull-request metadata is available.
- The worktree is not currently needed by another task or agent.
- The user authorized cleanup, including remote branch deletion when that is in scope.

Never use `--force` to bypass a failed safety check. Never delete, reset, stash, or overwrite uncertain work. Do not remove the repository root worktree. If a branch is not an ancestor, a worktree is dirty, or remote state cannot be established, preserve it and report the blocker.

## Cleanup

Use exact paths and branch names captured during the audit.

1. Normalize a stale root checkout only after proving that it contains no unique work and receiving authorization for any reset. Update the local default branch to the fetched remote using a fast-forward where possible.
2. Remove each verified task checkout with `git worktree remove <exact-path>`.
3. Delete its local branch with `git branch -d <exact-branch>`. Stop if Git refuses.
4. Delete merged remote task branches only when authorized and their exact names were verified. Do not delete the default remote branch.
5. Run `git fetch --prune`, `git worktree prune` when warranted, and a final inventory.

Finish with the resulting default-branch status, remaining worktrees and branches, actions taken, and anything intentionally preserved. State whether deleted branches remain recoverable from merged history.
