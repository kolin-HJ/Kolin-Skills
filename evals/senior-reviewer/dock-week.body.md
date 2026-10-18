perf(amazon-weekly): compare against the item's dock week computed once

For planners: no change.

For engineers: computeAmazonWeeklyPlan already computes dockWeek once per item. The stockout check still called isBeforeDockWeek for every week, which parsed the dock date and found its ISO Monday again each time. It now compares w < dockWeek. The result is the same, including a missing or empty dock date, which gives null and so "not before dock". isBeforeDockWeek stays for the Amazon Plan grid's own callers.

Verified: calc amazon tests pass (68). Replacing the check with false fails "pre-dock Amazon warnings > ignores pre-dock stockouts without hiding later shortages", so the line is covered.

