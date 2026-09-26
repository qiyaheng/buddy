---
name: release-desktop
description: Release a new SMEbuddy version — bump version, commit, push main, create and push v-prefixed tag, verify GitHub Actions macOS build. Use when the user says 发布, 打标签, release, push tag with a version number. Do not use for local-only packaging with npm run package:win.
---

# Release Desktop

Execute the exact release flow below. The user provides the semver version (e.g. `0.1.3`); the git tag is the same version with a `v` prefix (`v0.1.3`).

## Facts

- Remote: `https://github.com/qiyaheng/buddy.git`, branch `main`
- Tag push triggers `.github/workflows/build.yml` ("Build Desktop Installers") which builds macOS dmg/zip and publishes them to the GitHub Release
- Shell is PowerShell on Windows — never use Bash heredoc (`<<EOF`); build multi-line commit messages with multiple `-m` flags
- The Windows installer is a separate, independent step (`npm run package:win`); it is not part of this skill unless explicitly requested

## Steps

1. **Pre-checks**
   - `git status --short` and `git tag --list` — confirm the new tag does not already exist locally
   - Review every changed file. Stage only files belonging to this release; never `git add -A`
   - If a stray `6.0` file exists at repo root, delete it (legacy artifact from backend builds) and note it
   - If backend (`backend/app/`) code changed, run the test suite first:
     `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` — all tests must pass

2. **Bump version** in [package.json](file:///d:/AIproject/jobTwo/work_buddy/package.json): set `"version"` to the release version

3. **Commit** with a Conventional Commits message, staging explicit paths:
   `git add <files>; git commit -m "fix: ..." -m "bump version to X.Y.Z"`

4. **Push code, then tag** (in this order, separate commands):
   - `git push origin main`
   - `git tag vX.Y.Z`
   - `git push origin vX.Y.Z`
   - Success criterion: output contains `old..new main -> main` and `[new tag] vX.Y.Z -> vX.Y.Z`

5. **Verify the workflow triggered** via GitHub API (no `gh` CLI on this machine — use WebFetch):
   `https://api.github.com/repos/qiyaheng/buddy/actions/runs?per_page=2`
   - Confirm the newest run has `head_branch` equal to the new tag and `status` of `queued` or `in_progress`
   - If no matching run appears after one re-check, report it — do not claim the build started

6. **Report**: commit SHA, pushed tag, and the Actions run `html_url`; note that macOS artifacts appear under Releases when the build finishes

## Rules

- Do not amend, force-push, or reuse an existing tag; if the tag already exists remotely, stop and ask how to proceed
- Do not run `npm run package:win` or modify publish config as part of a release unless the user asks
- If push fails with a transient connection reset, retry once; on repeated failure, report instead of claiming success
