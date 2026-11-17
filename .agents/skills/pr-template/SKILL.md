---
name: pr-template
description: Fill Kira's pull request template from verified branch changes when asked to open or submit a PR.
---

# Kira Pull Request Template

1. Read `.github/PULL_REQUEST_TEMPLATE.md` and preserve its headings and checkbox labels.
2. Determine the base branch from the user's request, existing branch configuration, or Kira's `git-workflow` skill. Inspect commits and diff against that base.
3. Describe the reason for the change, actual files and behavior changed, and any related issue. Do not invent an issue number.
4. Check only verification steps that passed in this session. For Kira, use the backend and frontend commands from `AGENTS.md`; the template may list only a subset, so disclose additional required checks in the description.
5. Open the PR only when requested, using the repository's connected GitHub tool or `gh` with a body file. Report its URL.
