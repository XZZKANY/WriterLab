# WriterLab Runtime Notes

## Start Commands
- Backend:
  `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Frontend dev:
  `npm.cmd run dev -- --hostname 127.0.0.1 --port 3000`
- Frontend production check:
  `npm.cmd run build:node`
  `npm.cmd run start -- --hostname 127.0.0.1 --port 3000`

## Known `spawn EPERM` Issue
- In the current restricted Codex shell, Windows may block Node child processes created by `spawn` or `fork`.
- This is an environment restriction, not a Next.js code bug.
- When that happens, run frontend commands from a normal local shell or another non-restricted launch chain.

## Live Self-Check Order
1. Confirm backend root returns `WriterLab backend is running`.
2. Confirm `GET /api/knowledge/search` returns `retrieval_mode = "pgvector"`.
3. Start frontend and open `/editor`.
4. Verify branch flow:
   create branch -> diff -> adopt.
5. Verify workflow flow:
   run workflow -> poll status -> inspect generated draft / blocked result / auto-applied result.

## Demo Data Repair
- A one-time demo repair script is available at [fix_demo_garbled_data.py](/D:/WritierLab/WriterLab-v1/scripts/fix_demo_garbled_data.py).
- Dry run:
  `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe D:\WritierLab\WriterLab-v1\scripts\fix_demo_garbled_data.py`
- Apply:
  `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe D:\WritierLab\WriterLab-v1\scripts\fix_demo_garbled_data.py --apply`
- The script only touches a few explicit demo IDs and skips general user data.
