## Why

Access was a per-section level plus one `reporting.view.*` capability per report, edited one person at a time. A section level could not separate two pages in the same section, most Demand and Supply pages had no read guard at all (only their actions checked the level), and nobody could see who held what or give ten people the same access. Requested: permissions by page, read or write where a page is interactive (write includes read), and an Access page that manages many people and shows who has what.

## Scope

- **Model.** A page grant is the capability `<page id>:read` or `<page id>:write`, using the route table's ids, stored in `capability_grants` next to the extra permissions. `can()` treats write as read. `lib/permissions.ts` holds one catalog (mode `view`, `edit` or `actions`), so `Capability` and the page ids are derived and a test fails until every route table page is in it or listed as open. Reasons and consequences are in `docs/adr/0162-page-access.md`.
- **Guards.** `requireCapability` and `requireCapabilityPage` now take a capability or an array (any of). No new guard name, so `scripts/gate-policy.json` only shrinks. Pages that had no read guard now have one. Actions shared by two pages accept either (`SUPPLY_GRID_READ/WRITE`, Variant and Channels for channel membership, Variant and Placeholder Items for placeholder actions). A failed page guard redirects to the user's first readable page, or `/not-invited`.
- **Nav.** Sidebar and top-nav tabs derive from the catalog; a tab only shows when the user can open a page in it.
- **Access page.** Bulk select, per-page None / Read / Read & write, group presets, five templates, copy access from another person, Undo toast, multi-email invite with live validation, remove with confirmation, and a clickable who-has-what matrix. Server actions write the net change in one transaction, block removing your own `users.manage`, skip admins, and only an admin can remove an admin.
- **Migration 0036.** Section levels and the retired `reporting.view.*`, `reporting.items.manage` and `reporting.order_reservations.manage` rows become page grants; the retired rows are deleted (the app parses every stored capability and fails on an unknown one). `section_access` is left in place, unread, and removed from the Drizzle schema.
- Docs: AGENTS.md, ADR 0162 (new), ADR 0100 and 0016, the settings feature map; the verify world guard watches `capability_grants` instead of `section_access`.

## Tradeoffs

- Page grants live in `capability_grants` instead of a new table, to keep the gate policy and the existing guards. The cost is that a page level is two possible rows per page (the app keeps one).
- Templates replace all page access and clear extra permissions, because no template should grant a high-risk permission.
- Undo restores a person's whole grant set from a snapshot, so it overwrites an edit another admin made in between. Access changes are not audited yet (follow-up).
- Rolling the app back past this change needs the database restored too, because older code fails on the new capability rows. `drizzle-kit push` on a local database offers to drop `section_access`; accepting is safe.

## Blast Radius

Behavior changes to expect:
- Members with no section grants lose Demand, Supply and Agents pages that had no read guard (two active prod members today; checked read-only on prod). They land on `/not-invited` until given access.
- Wholesale Comp planner notes need write on Wholesale Comp; the demand plan snapshot needs write on Variant; the PO Placement saves and Supply grid actions need write on a supply grid page; ten supply-plan write actions that had no guard now require one; Lead Time Exceptions overrides need write on that page.
- Refresh data needs read on a supply grid page.
- `/settings` shows to anyone with `users.manage` or `settings.manage`, not only admins.
- New Variant Demand keeps write for former Supply viewers, as its actions allowed.
- GET routes that only check "signed in" are unchanged; the access API shape drops `sections`.

## Verification

- `pnpm check` passes, including `pnpm guards`, `pnpm rules`, the baseline ratchet against `origin/staging` and 1,357 web tests; the permission logic has tests that were seen failing when the code they cover was broken.
- Migration 0036 run on a legacy fixture (with and without `section_access`), and dry-run on the staging database in an aborted transaction; every capability stored in prod maps to a known one (read-only queries).
- Driven with `pnpm -s verify` against a scratch database: bulk write, "Reports only" template then Undo restoring the exact prior rows, copy access, remove with confirmation, invite, the matrix, and a member with one page plus `users.manage` redirected to the first readable page with a filtered nav. Screenshots in `.verify/evidence/settings/` (not committed).
- Independent review by `senior-reviewer`; its cross-page write finding is fixed (Variant detail actions need Variant write) and the unconditional-delete edge in the migration is fixed.
- Not checked: dark mode and narrow widths.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
