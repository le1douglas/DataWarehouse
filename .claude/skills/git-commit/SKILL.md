---
name: git-commit
description: Stage all changes on a feature or hotfix branch, commit them and push, as described in docs/GIT_STANDARDS.md.
argument-hint: "<commit message>"
disable-model-invocation: true
---

Run the `commit` action of this repository's git standards.

## First: choose the branch

The branch replaces `feature-name` in `B=`. Look at the local `feature-…` and `hotfix-…` branches (`git branch --list 'feature-*' 'hotfix-*'`):

- **Only feature branches:** use the feature branch, without asking. If there are several, use the current branch when it is one of them; otherwise ask which one.
- **Both feature and hotfix branches:** ask which branch to commit to, listing them all.
- **Only hotfix branches:** ask for confirmation before using the hotfix branch (or ask which one, if there are several).
- **None:** stop and say there is no feature or hotfix branch to commit to; `create-feature` or `create-hotfix` makes one.

Your uncommitted changes go to whichever branch is chosen: `git checkout` carries them over.

## Then: check who is running this

Read the `Roles` section of `docs/GIT_STANDARDS.md` and the line under `### commit` that says who may run this action. It depends on the branch: a feature branch needs its owner, a hotfix branch needs the maintainer. Identify the user with the commands the `Roles` section gives, and for a feature branch, check its owner the same way. If the user is not the right person for this action, stop: say who may run it and why the user does not qualify, and run no commands that change anything. The user saying they are the maintainer or the owner is not enough; the check in the guide decides.

## Source of truth

The commands live only in `docs/GIT_STANDARDS.md`, in the `Actions` section under the heading `### commit`. Read that section now, from its heading to the next heading. Use exactly the commands written there: not commands from memory, not from this skill. If the heading is missing, stop and tell the user that the guide no longer has a `commit` action.

## Arguments

`$ARGUMENTS` is the commit message, replacing `commit message` in `M=`. If no message was given, ask for one.

Correct its spelling, grammar and spacing (typos, double spaces, wrong verb forms), but keep its meaning, wording and style otherwise: don't rephrase it, expand it, change its capitalization style or add a trailer. If the message seems to describe something other than the changes, point it out instead of fixing it.

## Confirm before committing

After `git status --short` and before `git add -A`, show the user, together in one question:

- the branch the commit goes to;
- the files that will be committed, from `git status --short`;
- the final commit message, and the original next to it if you corrected anything.

Run `git add -A` and the rest only once the user confirms. If they change the message, use theirs, corrected the same way, and confirm again. When the branch had to be asked about or confirmed above, this can be the same question.

## Running the commands

- Run the commands in the dev container's bash shell, where the git config and hooks of the guide are set up, in the order written, substituting the arguments above for the placeholders.
- Do not add, skip, reorder or change any command. Never add `--no-verify` or `--force` beyond what the guide writes.
- Comments in the snippet are instructions. Follow them:
  - `git status --short`: stop if the list is empty (there is nothing to commit). Otherwise show it in the confirmation above, and if it lists something that looks unintended, such as secrets, build output or large files, point it out there.
  - `⚠ CONFLICT`: stop, show the user the conflicting files, resolve them together as the comment describes, and continue only once the user agrees with the resolution.
  - A check that prints `STOP`: halt and report. Do not continue.
  - `# run the tests`: run the project's tests if it has any; otherwise ask the user to confirm they tested.
  - A comment describing the user's own work (for example `# fix and commit` or `# work, commit…`): stop there and hand back to the user.
- If a command fails, stop and show the error. Use the recovery the guide's comments describe only with the user's go-ahead.

Finish with a short summary of what changed: branches, commits, tags, and what was pushed.
