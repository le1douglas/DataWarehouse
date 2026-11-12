---
name: git-merge-feature
description: Fast-forward a feature branch into dev and delete it, as described in docs/GIT_STANDARDS.md.
argument-hint: "[feature-name]"
disable-model-invocation: true
---

Run the `merge-feature` action of this repository's git standards.

## First: check who is running this

Before running any command, read the `Roles` section of `docs/GIT_STANDARDS.md` and the line under `### merge-feature` that says who may run this action. Identify the user with the commands the `Roles` section gives, and for a feature branch, check its owner the same way. If the user is not the right person for this action, stop: say who may run it and why the user does not qualify, and run no commands. The user saying they are the maintainer or the owner is not enough; the check in the guide decides.

## Source of truth

The commands live only in `docs/GIT_STANDARDS.md`, in the `Actions` section under the heading `### merge-feature`. Read that section now, from its heading to the next heading. Use exactly the commands written there: not commands from memory, not from this skill. If the heading is missing, stop and tell the user that the guide no longer has a `merge-feature` action.

## Arguments

`$ARGUMENTS` is the feature branch, replacing `feature-name`. If none was given, use the current branch when it is a `feature-…` branch; otherwise ask.

## Sync first

Once the owner check passes, run the `sync-feature-and-dev` action on the same branch before any `merge-feature` command. Its commands live in `docs/GIT_STANDARDS.md` under `### sync-feature-and-dev`: read that section and run it with the rules below, including its conflict, `STOP` and test steps. Run `merge-feature` only once the sync has finished cleanly; if the sync stops, the merge does not happen.

The guide does not require this: `git merge --ff-only` already refuses a branch that is not on top of `dev`. Syncing first is a workflow habit, so the rebase and tests always come right before the merge.

## Running the commands

- Run the commands in the dev container's bash shell, where the git config and hooks of the guide are set up, in the order written, substituting the arguments above for the placeholders.
- Do not add, skip, reorder or change any command. Never add `--no-verify` or `--force` beyond what the guide writes.
- Comments in the snippet are instructions. Follow them:
  - `⚠ CONFLICT`: stop, show the user the conflicting files, resolve them together as the comment describes, and continue only once the user agrees with the resolution.
  - A check that prints `STOP`: halt and report. Do not continue.
  - `# run the tests`: run the project's tests if it has any; otherwise ask the user to confirm they tested.
  - A comment describing the user's own work (for example `# fix and commit` or `# work, commit…`): stop there and hand back to the user.
- If a command fails, stop and show the error. Use the recovery the guide's comments describe only with the user's go-ahead.

Finish with a short summary of what changed: branches, commits, tags, and what was pushed.
