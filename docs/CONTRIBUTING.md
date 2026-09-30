# Contributing

This repo follows the ParkviewLab conventions; the authoritative, org-wide version of all of this is the [ParkviewLab handbook](https://github.com/ParkviewLab/handbook/tree/main). The essentials:

## Branch & PR flow

- Branch off `develop` into an ephemeral worktree named with a prefix: `feature-`, `bug-`/`fix-`, `doc-`, `test-`, `ops-`, `ci-`, `build-`, `release-` (hyphen, not slash). See the handbook's `branching.md`.
- Open a PR into `develop`. The repo is merge-commit only, so the merge button can only make a merge commit; merging is the maintainer's action.
- Releases are cut from `main` via the CLI (`git merge --no-ff develop`, then bump + tag), not a PR, and end with the back-merge pull request from `back-merge-<tag>`, which `git back-merge` opens, checks and merges. See the handbook's `releases.md`.

## Commit / PR-title convention

A PR is merged with a merge commit titled `<PR title> (#N)`, so the PR title becomes the commit subject. Prefix every PR title with a [Conventional Commit](https://www.conventionalcommits.org/) type (`feat:`, `fix:`, `perf:`, `refactor:`, `docs:`, `test:`, `revert:`, or `chore:` / `ci:` / `build:` / `style:` for maintenance), with a `!` after the type for a breaking change. This repository keeps no changelog and publishes no GitHub Release, by its slot (the comment at the head of `.github/workflows/release.yml`), but the prefix still says what kind of change a merge was.

## Local checks before opening a PR

Run the same checks CI requires, so the PR is green on arrival:

```bash
uv sync
uv run ruff check src/
uv run ty check src/
uvx --from "reuse[charset-normalizer]" reuse lint
```

A PR can't be merged until the required checks pass (lint and types, the licence check, REUSE, the version guard; see the handbook's `ci.md`). Push after each commit. See also `python-tooling.md`.

## Versioning

The version lives in `pyproject.toml` only; never hard-code it elsewhere, and never type it on a `git tag` line: use `git bump` / `git release` from [`dev-tools`](https://github.com/ParkviewLab/dev-tools). See `releases.md`.

## AI contributors

If the repo has a `docs/northstar.md`, read it first; and follow the behavioural contract in the handbook's `ai-collaboration.md` (notably: merging/tagging/releasing need an explicit, per-release go-ahead). The northstar leads: a change that alters intent amends it in the same PR, and an unintended disagreement between it and the code is a defect in the code.
