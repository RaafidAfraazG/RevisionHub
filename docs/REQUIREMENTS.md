# Requirements

## Business context

A small engineering team needs a consistent place to identify parts, trace revisions, review changes and share supporting files. Success means answering “what changed, why, and who approved it?” without manually comparing folders and spreadsheets.

## Traceability

| Business requirement | Functional requirement | Implementation / acceptance |
| --- | --- | --- |
| BR-01: Identify engineering items | FR-01: Unique part numbers, type and searchable number/name | Parts library rejects duplicates and finds seeded bicycle items. |
| BR-02: Preserve design iterations | FR-02: Sequential revision labels and lifecycle states | New revisions have empty draft BOMs; locked revisions reject edits. |
| BR-03: Understand the full structure | FR-03: Recursive BOM, positive quantities and cycle checks | BIKE-001 expands wheel/spoke structure; cycles across all revisions are rejected. |
| BR-04: Make proposals reviewable | FR-04: Multi-level same-part comparison | Four lists/counts, summed effective quantities and paths; different parts return 400. |
| BR-05: Explain revision substitutions | FR-05: Release-time child resolution and label comparison | Shared child moving A to B appears as REVISION_CHANGED; legacy fallback is documented. |
| BR-06: Exchange structure data | FR-06: CSV with seven specified columns | Root and all path occurrences export with multiplied quantities and formula-safe text. |
| BR-07: Keep design evidence together | FR-07: Upload/list/download/delete attachments | Allowed extensions, max 20 MiB, authenticated DRAFT writes and audit entries. |
| BR-08: Inspect without CAD software | FR-08: STL rotate/zoom/fit/reset, inline images, download STEP/PDF | Seeded RIM-101 shows a generated mesh; STEP displays its unsupported-preview note. |
| BR-09: Separate preparation/review/approval | FR-09: JWT roles, inboxes and creator exclusions | Engineer submits, independent reviewer reviews, independent approver releases. |
| BR-10: Release consistently | FR-10: Atomic release/obsolescence, cycle-scoped decisions | States/audit commit together; rejection requires comment and resubmission a fresh review. |
| BR-11: Monitor work and accountability | FR-11: Dashboard counts/charts/mean lead time/latest ten events | Zero states included, unavailable samples shown clearly, files traced in part history. |
| BR-12: Reproduce and explain the project | FR-12: Repeatable seed, eight tests, build and documentation | No duplicate seed records/files; diagrams, demo roles and local run commands provided. |

## Nonfunctional requirements

| Concern | Scope |
| --- | --- |
| Usability | Responsive navigation, labeled controls, text plus color in diffs, loading/empty/error states. |
| Integrity | Positive quantities, unique BOM child and part/revision label, transactional decisions/state changes. |
| Security | Password hashes, expiring JWTs, server-enforced draft/role checks, random storage names, CSV formula neutralization. Public read APIs remain a demo boundary. |
| Portability | Python/Node local setup and SQLite; optional documented PostgreSQL Compose configuration with persistent uploads. |
| Maintainability | Routers separated from graph/compare/workflow/audit services; two new tests preserve six regression tests. |

## Feasibility

**Technical:** FastAPI, SQLAlchemy and React cover the API, graph traversal and UI without commercial PLM tooling. Procedural binary STL generation uses the Python standard library. The catalogue contains bicycle and gearbox structures, with versioned idempotent seeding and reproducible benchmark fixtures.

**Operational:** Three fixed roles and seeded bicycle and gearbox assemblies make the workflow easy to demonstrate locally. SQLite and local storage fit portfolio use. Confidential manufacturing data would need restricted read APIs, frozen BOM baselines and stronger upload validation.

**Economic/schedule:** Open-source libraries and local operation avoid license/hosting costs. Scope excludes CAD conversion, enterprise identity, notifications and multi-tenancy. Eight focused tests and build/browser checks keep verification bounded; this is not enterprise validation or load testing.

## Three process-improvement ideas

1. **Risk-based review routing:** Classify safety, supplier and manufacturing impact, then assign relevant reviewers automatically. Measure waiting time and first-pass approval rate.
2. **Frozen release packages:** Pin child revisions and bundle BOM snapshots, files and approvals. Measure shop-floor clarification requests and wrong-revision incidents.
3. **Where-used analysis and notifications:** Identify parent assemblies affected by a change and notify owners on submission/rejection/release. Measure overdue reviews and downstream update omissions.
