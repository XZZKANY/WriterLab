"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { createProject, type ProjectResponse } from "@/lib/api/projects";
import { AppShell } from "@/shared/ui/app-shell";

export default function ProjectCreatePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!name.trim()) {
      setError("请输入项目名称。");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const payload = await createProject<ProjectResponse>({
        name: name.trim(),
        description: description.trim() || undefined,
        default_language: "zh-CN",
      });

      router.push(`/project/${payload.id}`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "创建项目失败。");
      setSubmitting(false);
    }
  }

  return (
    <AppShell title="Create a personal project" description="">
      <section className="mx-auto w-full max-w-[720px]">
        <div className="rounded-[32px] border border-white/8 bg-[#1b1b1b] px-6 py-6 shadow-[0_28px_80px_rgba(0,0,0,0.3)] sm:px-8 sm:py-8">
          <div className="max-w-[520px]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-zinc-500">
              New workspace
            </p>
            <h2 className="mt-3 text-[1.7rem] font-semibold tracking-[-0.04em] text-zinc-100">
              Start a new long-form writing project
            </h2>
            <p className="mt-3 text-sm leading-7 text-zinc-500">
              Give the project a stable name and a short brief. After creation, we will jump
              directly into the project detail workspace.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="mt-8 space-y-7">
            <div>
              <label
                htmlFor="project-name"
                className="text-base font-medium tracking-[-0.02em] text-zinc-100"
              >
                What are you working on?
              </label>
              <input
                id="project-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Name your project"
                className="mt-3 h-14 w-full rounded-[22px] border border-white/10 bg-[#232323] px-5 text-base tracking-[-0.02em] text-zinc-100 outline-none transition placeholder:text-zinc-500 focus:border-zinc-500"
              />
            </div>

            <div>
              <label
                htmlFor="project-description"
                className="text-base font-medium tracking-[-0.02em] text-zinc-100"
              >
                What are you trying to achieve?
              </label>
              <textarea
                id="project-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Describe your project, goals, subject, and writing direction..."
                className="mt-3 min-h-40 w-full rounded-[22px] border border-white/10 bg-[#232323] px-5 py-4 text-[1rem] leading-7 tracking-[-0.02em] text-zinc-100 outline-none transition placeholder:text-zinc-500 focus:border-zinc-500"
              />
            </div>

            {error ? (
              <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                {error}
              </div>
            ) : null}

            <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
              <Link
                href="/project"
                className="inline-flex h-12 items-center justify-center rounded-[18px] border border-white/10 px-5 text-sm font-medium tracking-[-0.02em] text-zinc-200 transition hover:border-zinc-500 hover:bg-white/5"
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex h-12 items-center justify-center rounded-[18px] bg-zinc-100 px-5 text-sm font-medium tracking-[-0.02em] text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "Creating..." : "Create project"}
              </button>
            </div>
          </form>
        </div>
      </section>
    </AppShell>
  );
}
