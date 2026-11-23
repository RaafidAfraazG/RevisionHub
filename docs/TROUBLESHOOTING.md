# Troubleshooting

## 1. Backend will not start / multipart support is missing

**Symptoms:** Python is not recognized, module import failure, or FastAPI requests `python-multipart`.

**Root cause:** Python is not on PATH, dependencies were installed into another interpreter, or the Phase 2 environment lacks the new package.

**Fix:** From the project root run `.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt`, then use that interpreter from `backend` to start Uvicorn. To create the environment on this machine without PATH activation: `C:\Users\Raafid\.local\bin\python3.12.exe -m venv .venv`. Restart the API after installing.

## 2. Frontend is blank / API requests fail

**Symptoms:** Network toast, Vite proxy error, port conflict or missing frontend modules.

**Root cause:** Backend is not on 8000, frontend is not on 5173, dependencies are missing, or another process owns the port. Opening built HTML directly bypasses proxy/routing.

**Fix:** Use the documented two-terminal commands, run `npm ci`, check `http://localhost:8000/api/health` and open `http://localhost:5173`. Stop only your own stale server before reusing a port. Set `API_PROXY_TARGET` before launching Vite if using another backend address. A production static host needs an `/api` reverse proxy and SPA fallback.

## 3. Login or ECR action fails

**Symptoms:** 401/403, empty inbox, locked revision or final approval rejected.

**Root cause:** Users were not seeded, JWT expired/key changed, role/creator rules prohibit action, or revision is no longer DRAFT.

**Fix:** Run `seed.py` and sign in with a documented demo login. Use the creating engineer for submission, reviewer for current-cycle review, then approver for final release. Reject with a comment and perform a fresh review after resubmission. Supply a stable `SECRET_KEY` across backend instances. Seed preserves existing passwords/decisions; it does not reset users or reopen released requests. Attachment writes also require DRAFT.

## 4. Viewer, attachment upload or download fails

**Symptoms:** Blank STL, 400/409/413, STEP has no preview or download returns 404.

**Root cause:** WebGL unavailable, invalid STL bytes, extension/size/state checks reject a file, STEP unsupported, or uploaded bytes are missing from disk.

**Fix:** Use a WebGL-capable browser and valid STL, then Reset view. Allowed extensions: `.stl`, `.step`, `.stp`, `.pdf`, `.png`, `.jpg`; max 20 MiB, nonempty, logged-in DRAFT writes. Download STEP into CAD. Back up `backend/uploads` with the database and retain Compose's uploads volume. Rerun seed to regenerate the missing demo STL. Extension checks do not guarantee valid mesh/image content.

## 5. Diff, CSV quantities or dashboard lead time look unexpected

**Symptoms:** Duplicate CSV part rows, historical/current child labels differ, one parent change alters many descendant quantities, or release time is “—”.

**Root cause:** CSV preserves occurrences/current resolution; compare aggregates quantities and uses release-time history for released roots. Parent multipliers propagate. Imported timestamps can invoke legacy fallback. Seeded part releases without an audited ECR submission are not lead-time samples.

**Fix:** Read `quantity` per parent and `total_quantity` as the path product; sum repeated part numbers if desired. Inspect before/after diff paths and baseline direction. Retain valid release history; pinned snapshots are future work. Complete an ECR through reviewer/approver and reload Dashboard for a sample. Repair any externally introduced BOM cycle before compare/export.
