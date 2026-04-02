"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  FolderKanban,
  LayoutDashboard,
  Settings,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";

type WorkspaceShellProps = {
  title: string;
  description: string;
  eyebrow?: string;
  actions?: ReactNode;
  children: ReactNode;
};

type SidebarItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  match: RegExp;
};

const sidebarItems: SidebarItem[] = [
  { href: "/", label: "项目总览", icon: LayoutDashboard, match: /^\/$/ },
  { href: "/project", label: "项目列表", icon: FolderKanban, match: /^\/project(\/.*)?$/ },
  { href: "/runtime", label: "运行诊断", icon: Activity, match: /^\/runtime(\/.*)?$/ },
  { href: "/settings", label: "模型设置", icon: Settings, match: /^\/settings(\/.*)?$/ },
];

export function WorkspaceShell({
  title,
  description,
  eyebrow = "WriterLab",
  actions,
  children,
}: WorkspaceShellProps) {
  const pathname = usePathname();

  return (
    <main className="min-h-screen bg-[#171717] text-zinc-200">
      <div className="flex min-h-screen">
        <aside className="hidden w-72 shrink-0 border-r border-white/6 bg-[#141414] px-4 py-5 lg:flex lg:flex-col">
          <div className="px-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-zinc-500">
              {eyebrow}
            </p>
            <h1 className="mt-3 text-[2rem] font-semibold tracking-[-0.05em] text-zinc-100">
              项目工作区
            </h1>
          </div>

          <div className="mt-8 border-t border-white/6 pt-6">
            <p className="px-3 text-[11px] uppercase tracking-[0.28em] text-zinc-600">工作区</p>
            <nav className="mt-3 space-y-1">
              {sidebarItems.map((item) => {
                const Icon = item.icon;
                const active = item.match.test(pathname);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm tracking-[-0.01em] transition ${
                      active
                        ? "bg-zinc-800/90 text-zinc-100"
                        : "text-zinc-500 hover:bg-zinc-800/50 hover:text-zinc-200"
                    }`}
                  >
                    <Icon size={17} strokeWidth={1.75} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="mt-auto rounded-2xl border border-white/6 bg-[#1d1d1d] p-4">
            <div className="flex items-center gap-2 text-sm font-medium tracking-[-0.02em] text-zinc-100">
              <Sparkles size={15} strokeWidth={1.8} />
              项目视图
            </div>
            <p className="mt-2 text-sm leading-6 text-zinc-500">
              统一项目、编辑、设定和运行时入口，让所有页面都落在同一套暗色工作区语境里。
            </p>
          </div>
        </aside>

        <div className="flex-1">
          <div className="mx-auto flex w-full max-w-7xl flex-col px-5 py-6 sm:px-8 lg:px-10">
            <header className="mb-8 border-b border-white/6 pb-6">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  {eyebrow ? (
                    <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-zinc-500">
                      {eyebrow}
                    </p>
                  ) : null}
                  <h1 className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-zinc-100">
                    {title}
                  </h1>
                  {description ? (
                    <p className="mt-3 max-w-3xl text-sm leading-7 text-zinc-500">
                      {description}
                    </p>
                  ) : null}
                </div>
                {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
              </div>
            </header>

            <div className="space-y-6">{children}</div>
          </div>
        </div>
      </div>
    </main>
  );
}
