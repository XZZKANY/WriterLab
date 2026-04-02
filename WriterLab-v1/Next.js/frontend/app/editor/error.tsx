"use client";

export default function EditorError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="min-h-screen bg-neutral-100 px-4 py-8 text-neutral-900">
      <div className="mx-auto max-w-5xl rounded-3xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold">编辑工作区加载失败</h2>
        <p className="mt-3 text-sm text-neutral-600">{error.message}</p>
        <button
          className="mt-4 rounded-full bg-neutral-900 px-4 py-2 text-sm text-white"
          onClick={reset}
        >
          重试
        </button>
      </div>
    </main>
  );
}
