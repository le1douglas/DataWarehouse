---
name: git-merge-hotfix
description: Merge a hotfix into main with a tag, then into dev, as described in docs/GIT_STANDARDS.md.
argument-hint: "[hotfix-name] [vX.Y.Z]"
disable-model-invocation: true
---

Run the `merge-hotfix` action of this repository's git standards.

## First: check who is running this

Before running any command, read the `Roles` section of `docs/GIT_STANDARDS.md` and the line under `### merge-hotfix` that says who may run this action. Identify the user with the commands the `Roles` section gives, and for a feature branch, check its owner the same way. If the user is not the right person for this action, stop: say who may run it and why the user does not qualify, and run no commands. The user saying they are the maintainer or the owner is not enough; the check in the guide decides.

## Source of truth

The commands live only in `docs/GIT_STANDARDS.md`, in the `Actions` section under the heading `### merge-hotfix`. Read that section now, from its heading to the next heading. Use exactly the commands written there: not commands from memory, not from this skill. If the heading is missing, stop and tell the user that the guide no longer has a `merge-hotfix` action.

## Arguments

`$ARGUMENTS` holds the hotfix branch (replacing `hotfix-name` in `H=`) and the new version (replacing `vX.Y.Z` in `V=`). If the branch is missing, use the current branch when it is a `hotfix-…` branch; otherwise ask. If the version is missing, propose the patch +1 of the latest `v*` tag, following the guide's `Naming` section (with the `-alpha` suffix while the guide asks for it, for example `v0.3.1-alpha` after `v0.3.0-alpha`), and ask the user to confirm. Always confirm the version before the tag is created.

## Running the commands

- Run the commands in the dev container's bash shell, where the git config and hooks of the guide are set up, in the order written, substituting the arguments above for the placeholders.
- Do not add, skip, reorder or change any command. Never add `--no-verify` or `--force` beyond what the guide writes.
- Comments in the snippet are instructions. Follow them:
  - `⚠ CONFLICT`: stop, show the user the conflicting files, resolve them together as the comment describes, and continue only once the user agrees with the resolution.
  - A check that prints `STOP`: halt and report. Do not continue.
  - `# run the tests`: run the project's tests if it has any; otherwise ask the user to confirm they tested.
  - A comment describing the user's own work (for example `# fix and commit` or `# work, commit…`): stop there and hand back to the user.
- If a command fails, stop and show the error. Use the recovery the guide's comments describe only with the user's go-ahead.

## Afterwards: offer to sync feature branches

Only once every step of `merge-hotfix` has finished, including the clean-up, look at the local feature branches (`git branch --list 'feature-*'`). If there are none, skip this section.

For each one, check its owner the way the `Roles` section describes. Offer to sync only the branches the user owns, or that have no commits yet; list any others as needing their owner to sync.

Ask the user, in one question, whether to sync the hotfix into those branches now, and which ones. For each branch they pick, run the `sync-feature-and-dev` action: its commands live in `docs/GIT_STANDARDS.md` under `### sync-feature-and-dev`. Read that section and run it with the rules above, including its conflict, `STOP` and test steps. If a sync stops, report it and don't start the next one. If the user says no, just mention that the branches pick up the hotfix the next time they run `sync-feature-and-dev`.

The guide does not require this step: the hotfix reaches feature branches at their next sync anyway. Offering it here is a workflow habit, so work in progress gets the fix right away.

## Afterwards: the prod stack

The prod stack is built from the tag, not from `main`, and it needs Docker, which the dev container does not have. Do not touch it: tell the user that, on Windows, they set `RELEASE` in `docker/.env.prod` to the new tag and run `powershell -ExecutionPolicy Bypass -File docker\03_setup_prod.ps1`, which ends with `prod setup done, on <tag>`.

Finish with a short summary of what changed: branches, commits, tags, and what was pushed.
