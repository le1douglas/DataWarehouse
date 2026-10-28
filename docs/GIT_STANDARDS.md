# Git standards

How branches, releases and hotfixes are managed. The model is GitLab Flow with a production branch: one branch to
work on, one branch that is what prod runs, and prod moved forward to a tested commit of dev at each release.

## Branches

| Branch | Lives | What it is |
|---|---|---|
| `dev` | forever | all work is committed here, directly; never closed, never branched out again after a release |
| `prod` | forever | the latest release; only ever fast-forwarded, never committed to |
| `hotfix/<version>` | hours | a fix on top of the latest release; deleted once merged back |

- `prod` always points to a commit that is also on `dev` (or on a hotfix branch merged into `dev`).
- The default branch on GitHub is `dev`.

## Releases

A release is a tag on a `dev` commit, and `prod` moved to that commit:

```bash
git switch dev
git pull
git push origin dev               # the commits to release are on GitHub
git tag -a v0.1.6-alpha -m "v0.1.6-alpha: <what the release brings, one line>"
git push origin dev:prod          # refused when it is not a fast-forward: see "Things to avoid"
git push origin v0.1.6-alpha      # the tag too: git push never sends tags on its own
git fetch origin prod:prod        # the local prod branch to where GitHub's now is
```

- Release only a commit that passed the full loop (`dbt build`) on dev.
- The tag push is what makes the release exist outside this PC: without it, `03_setup_prod.ps1` elsewhere cannot
  find the tag, `01_setup_env.ps1` picks an older one, and GitHub does not list it.
- A local `prod` does not follow GitHub's on its own; the last line moves it, without switching to it.
- Then rebuild prod, which is built from the tag, not from the branch:
  - set `RELEASE` in `docker/.env.prod` to the tag
  - `powershell -ExecutionPolicy Bypass -File docker\03_setup_prod.ps1` → ends with `prod setup done, on <tag>`
  - images of the previous release stay: going back is setting `RELEASE` back and running the script again
- Tags are annotated (`-a`) and follow [semantic versioning](https://semver.org): `vMAJOR.MINOR.PATCH`, with
  `-alpha` while the warehouse is not in real use. A hotfix raises PATCH, a normal release MINOR.
- Optionally publish the tag as a GitHub Release, so the Releases page lists every version.

## Hotfixes

A fix for prod that cannot wait for the unreleased work on `dev`. It starts from the latest release, never from
`dev`:

```bash
git switch -c hotfix/v0.1.7-alpha v0.1.6-alpha   # from the release prod runs
# commit the fix
git tag -a v0.1.7-alpha -m "v0.1.7-alpha: <the fix>"
git push origin hotfix/v0.1.7-alpha:prod         # a fast-forward: the fix sits on top of the release
git push origin v0.1.7-alpha
git fetch origin prod:prod                       # local prod to the fix, or the merge below merges nothing
git switch dev
git merge prod                                   # dev gets the fix
git push origin dev
git branch -d hotfix/v0.1.7-alpha
```

- Then rebuild prod on the new tag, as under **Releases**.
- The merge into `dev` is what keeps the next release a fast-forward: after it, the fix is an ancestor of `dev`.
- The next normal release takes the next number (`v0.1.8-alpha`).

## Commits

- One logical change per commit, small enough to explain in one line.
- Subject in the imperative, at most about 50 characters, no full stop: `add mother rooms to datastreamer`, not
  `added support for mother rooms`.
- When the reason is not obvious, a blank line and a body that says why, not what.
- Never committed: the env files in `docker/` (`.env*`), passwords, `user_input/corrections_dev/`. They are in
  `.gitignore`; do not force-add them.

## Things to avoid

- **Committing to `prod`:** `prod` would get a commit `dev` does not have, and every release after it is refused.
- **A pull request into `prod`:** GitHub's merge buttons (merge, squash, rebase) all create new commits, with the
  same effect. Release with `git push origin dev:prod`.
- **Cherry-picking a hotfix into `dev`:** the copy has another commit id, so `prod` still holds a commit `dev`
  lacks. Merge `prod` into `dev` instead.
- **Rebasing or force-pushing `dev` or `prod`:** both are shared and pushed; rewriting them breaks every clone and
  the fast-forward. On GitHub, protect both branches against force pushes and deletion.
- **Moving or deleting a pushed tag:** a tag is what prod was built from. A wrong release gets a new tag, not an
  edited one.
- **Lightweight tags** (`git tag v0.1.6-alpha` without `-a`): no author, date or message.
- **Releasing a commit that was not tested on dev:** run the full loop (`dbt build`) on `dev` first.
- **Branching a hotfix from `dev`:** it would carry the unreleased work into prod.
- **Long-lived hotfix branches, or merging `dev` into one:** a hotfix holds the fix and nothing else.
- **Feature branches that live for weeks:** work goes on `dev`; a branch, when one is needed for an experiment,
  lives a day or two and is merged or deleted.
