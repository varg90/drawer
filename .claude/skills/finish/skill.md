---
name: finish
description: >
  Finalize work: review changed code with /simplify, commit all changes,
  and create a GitHub PR. Use when the user says /finish or asks to wrap up,
  finalize, or ship the current branch.
---

# Finish

Finalize the current branch: review, commit, and create a PR.

## Steps

Execute these steps in order. Stop and report if any step fails.

### 1. Review with Simplify

Invoke the `simplify` skill to review changed code for reuse, quality, and efficiency. Fix any issues found.

### 2. Run Tests

Run the full test suite:
```
python -m pytest tests/ -q
```
If tests fail, fix the issues before proceeding. Do not continue with failing tests.

### 3. Ensure Feature Branch

Check the current branch. If on `main`:
- Create a feature branch from the changes: `git checkout -b feat/<short-description>`
- The branch name should reflect the work done (e.g. `feat/dpi-fixes`, `fix/url-dialog-bugs`)

If already on a feature branch, continue.

### 4. Commit Remaining Changes

Check `git status` for any uncommitted changes. If there are changes:
- Stage relevant files (not .env, credentials, or generated files)
- Commit with a clear message summarizing the work

If there are no changes (everything already committed), skip this step.

### 5. Push Branch

Push the feature branch to origin:
```
git push -u origin <branch-name>
```

Never push directly to main.

### 6. Create Pull Request

Create a PR using `gh pr create` with:
- Short title (under 70 characters) summarizing the branch's work
- Body with:
  - Summary section (3-5 bullet points of key changes)
  - Test plan section (what to verify)
- Target the `main` branch

Format:
```
gh pr create --title "title" --body "$(cat <<'EOF'
## Summary
- bullet points

## Test plan
- [ ] verification steps

Generated with Claude Code
EOF
)"
```

### 7. Report

Show the PR URL and a brief summary of what was shipped.
