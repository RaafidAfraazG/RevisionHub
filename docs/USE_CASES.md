# Use cases

## UC-01 — Define a part and revision

**Actor:** Authenticated team member.  
**Precondition:** Logged in; part number unused.

1. Create a component/assembly with number and name from Parts.
2. Open the part and Create Next Revision.
3. Add a change note and save.

**Result:** A unique part has revision A in DRAFT with an empty BOM. Duplicate part numbers show an error.

## UC-02 — Develop a multi-level BOM

**Actor:** Authenticated team member.  
**Precondition:** Parent revision is DRAFT; child parts exist.

1. Add children with positive quantities to the revision.
2. Add deeper lines to subassembly drafts.
3. Expand the tree and inspect resolved child revisions.
4. Remove an unwanted direct line.

**Result:** Structure changes are audited. Duplicate children, nonpositive quantities and cycles are rejected. Locked revisions remain read-only.

## UC-03 — Compare a proposal

**Actor:** Engineer, reviewer or approver.  
**Precondition:** One part has at least two revisions.

1. Open Compare from the part or the previous-revision shortcut on a revision/ECR.
2. Select baseline and proposed revisions.
3. Inspect summary counts and colored rows.
4. Check effective quantities and before/after paths; optionally swap direction.

**Result:** Full-structure added/removed parts and quantity/revision changes are visible. Same-revision diff is empty; different-part API comparison returns 400. An item may have two change categories.

## UC-04 — Export a BOM

**Actor:** Team member viewing a revision.  
**Precondition:** Revision exists; expanded structure has no cycle.

1. Open the revision's BOM page.
2. Choose Export CSV.
3. Open the download in a spreadsheet.
4. Inspect levels, per-parent quantities and effective quantities.

**Result:** The seven required columns contain a level-0 root and all path occurrences. Repeated parts appear per path; formula-like text is neutralized.

## UC-05 — Attach and inspect design evidence

**Actor:** Logged-in team member for writes; viewer for reads.  
**Precondition:** DRAFT revision for writes; allowed nonempty file up to 20 MiB.

1. Upload STL, STEP/STP, PDF, PNG or JPG from Attachments.
2. Select the file.
3. Rotate/zoom/reset an STL or inspect an image; download STEP/PDF.
4. Delete an unwanted attachment while the revision is still DRAFT.

**Result:** Metadata and bytes persist with upload/delete audit entries. Locked revisions reject writes. RIM-101 A has a seed-generated STL for a released-revision preview demo.

## UC-06 — Submit an engineering change

**Actor:** Creating engineer.  
**Precondition:** An unclaimed draft exists or a new revision can be created.

1. Create an ECR with part, title, reason and optional draft revision.
2. Complete its BOM and attachments.
3. Compare the proposal with its predecessor.
4. Submit for review.

**Result:** ECR/revision become IN_REVIEW, edits lock, submission is audited and work enters the reviewer inbox. Only the creating engineer may submit.

## UC-07 — Review, rework and release

**Actors:** Independent reviewer, creating engineer, independent approver.  
**Precondition:** Submitted ECR with a locked proposed revision.

1. Reviewer inspects proposal, BOM diff and files.
2. If needed, reject with a comment; engineer updates the unlocked draft and resubmits.
3. Reviewer approves the current cycle.
4. Approver grants final approval.
5. Inspect states and timeline.

**Result:** Release, previous-release obsolescence and audit commit together. Old approvals cannot authorize a new cycle; self-review/self-approval and premature approval are rejected.

## UC-08 — Monitor product/change activity

**Actor:** Any logged-in team member.  
**Precondition:** Valid session; data may be empty or seeded.

1. Sign in and land on Dashboard.
2. Inspect totals and revision/ECR distributions.
3. Inspect mean submission-to-release hours and sample count.
4. Read the newest ten events; open Inbox for assigned work.

**Result:** Current workload and accountability are visible. No completed samples show an unavailable metric. Empty activity is explained; expired sessions return to login.
