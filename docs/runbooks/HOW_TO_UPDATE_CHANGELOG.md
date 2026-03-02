---
description: "Step-by-step instructions for keeping CHANGELOG.md aligned with weekly work."
tags:
  - docs
  - changelog
---

# HOW TO UPDATE CHANGELOG

This repo keeps a rolling weekly changelog with a fixed set of sections so anyone can quickly scan recent activity. Follow the rubric below any time you want to add a new period to `CHANGELOG.md`.

## 1. Determine the week window

- The changelog is grouped by week ranges (`YYYY-MM-DD to YYYY-MM-DD`). Use the Monday-to-Sunday range that just ended. If you miss a week, add the missing block above the existing entries.
- Collect the merged PRs for that week via `git log --since=YYYY-MM-DD --until=YYYY-MM-DD` (or from your release notes) and confirm titles/descriptions from the GitHub PR page.

## 2. Section hierarchy

Every weekly block must contain these sections: `Backend/API`, `UI/frontend`, `ML`, `Platform`, `Docs/Quality`, `Automation/CI`, and `Bug Fixes`. Add the sections even if a given week has no PRs for that area.

For each section:

1. Write a bullet that starts with `- High-level summary:` followed by 2–3 sentences summarizing the week’s work within that bucket.
1. Follow with `- PRs:` and a bullet list of the week’s PRs that belong in that section. Each PR entry must be in the form:

```markdown
- [https://github.com/<org>/<repo>/pull/<number>](https://github.com/<org>/<repo>/pull/<number>): <Title of PR>. <1-2 sentence description of the fix.
```

1. If there are no PRs for that section, write `- PRs:` followed by a nested bullet `- _None this week._` indented by two spaces.

Use discretion when categorizing PRs. For example, fixes that touch backend data layers or API contracts go under `Backend/API`, whereas UI composition work belongs under `UI/frontend`. Testing/quality/linting improvements belong under `Docs/Quality`, while automation jobs and CI tooling updates go under `Automation/CI`. Bug fixes that aren’t captured by another section (e.g., regression fixes, flaky tests) belong under `Bug Fixes`.

## 3. Final checks

- Keep the newest week at the top so readers see the latest work first.
- Ensure summaries are short, factual, and neutral; avoid speculation.
- Double-check links point to the correct GitHub PR numbers and include the full URL.
- Run `git status` to confirm `CHANGELOG.md` is staged/modified as desired.

## 4. Optional cross-check (recommended)

- Compare against `docs/weekly_updates` to see if there are additional details you should capture. The weekly update files are a convenient source for grouped PR lists that can help you classify each change.
