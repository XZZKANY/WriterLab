# WriterLab Frontend Debug Console

This Next.js app is the WriterLab debug console. It is not the primary end-user client; it exists to inspect workflow state, provider fallback, context compilation, and runtime readiness.

## Start Order
1. Start the backend first:
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\start-backend.ps1`
2. Run frontend checks:
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1`
3. Start the frontend:
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\start-frontend.ps1`

## Important Commands
- Dev server:
  `npm run dev`
- Type check:
  `npm run typecheck`
- Production build check:
  `npm run build:node`

## Runtime Expectations
- Open `/editor` after the backend is available at `http://127.0.0.1:8000`.
- Use the `Runtime Readiness` and `Workflow Debug` panels to confirm:
  backend health
  workflow runner state
  recovery scan status
  pgvector readiness
  provider matrix availability

## Known Windows Caveat
- In restricted shells, `npm run build:node` may fail with `spawn EPERM`.
- This is treated as an environment limitation unless TypeScript compilation also fails.
