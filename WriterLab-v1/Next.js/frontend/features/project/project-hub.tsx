"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Archive,
  BookOpenText,
  ChevronDown,
  Eye,
  MoreVertical,
  PencilLine,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import {
  deleteProject,
  fetchProjects,
  type ProjectDeleteResponse,
} from "@/lib/api/projects";
import { AppShell } from "@/shared/ui/app-shell";

type Project = {
  id: string;
  name: string;
  description?: string | null;
  genre?: string | null;
  default_language: string;
  created_at: string;
  updated_at: string;
};

type ProjectCardProps = {
  project: Project;
  menuOpen: boolean;
  deleting: boolean;
  onToggleMenu: (projectId: string) => void;
  onCloseMenu: () => void;
  onArchive: (projectName: string) => void;
  onDelete: (project: Project) => void;
};

type CardActionLink = {
  href: string;
  label: string;
  icon: typeof Eye;
  destructive?: false;
};

type CardActionButton = {
  label: string;
  icon: typeof Archive;
  onClick: () => void;
  destructive?: boolean;
  disabled?: boolean;
};

type CardAction = CardActionLink | CardActionButton;

function isLinkAction(action: CardAction): action is CardActionLink {
  return "href" in action;
}

export default function ProjectHub() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [deletingProjectId, setDeletingProjectId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const payload = await fetchProjects<Project[]>();
        if (!cancelled) {
          setProjects(payload);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "读取项目列表失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function handleWindowClick() {
      setOpenMenuId(null);
    }

    if (openMenuId) {
      window.addEventListener("click", handleWindowClick);
    }

    return () => {
      window.removeEventListener("click", handleWindowClick);
    };
  }, [openMenuId]);

  const filteredProjects = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const nextProjects = [...projects].sort(
      (left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at),
    );

    if (!normalizedQuery) {
      return nextProjects;
    }

    return nextProjects.filter((project) => {
      const haystack = [
        project.name,
        project.description || "",
        project.genre || "",
        project.default_language,
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(normalizedQuery);
    });
  }, [projects, query]);

  async function handleDeleteProject(project: Project) {
    const confirmed = window.confirm(`确定删除“${project.name}”吗？删除后不会保留兼容数据。`);
    if (!confirmed) {
      return;
    }

    setDeletingProjectId(project.id);
    setError(null);
    setNotice(null);

    try {
      const payload = await deleteProject<ProjectDeleteResponse>(project.id);
      if (!payload.deleted) {
        throw new Error("删除项目失败");
      }

      setProjects((current) => current.filter((item) => item.id !== project.id));
      setNotice(`已删除项目“${project.name}”。`);
      setOpenMenuId((current) => (current === project.id ? null : current));
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "删除项目失败");
    } finally {
      setDeletingProjectId(null);
    }
  }

  return (
    <AppShell
      title="Projects"
      description=""
      actions={
        <Link
          href="/project/new"
          className="inline-flex items-center gap-2 rounded-2xl bg-zinc-100 px-4 py-2.5 text-sm font-medium tracking-[-0.02em] text-black transition hover:bg-zinc-200"
        >
          <Plus size={16} strokeWidth={2} />
          New project
        </Link>
      }
    >
      <section className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <label className="relative block w-full xl:max-w-[760px] xl:flex-1">
          <Search
            size={18}
            strokeWidth={1.8}
            className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500"
          />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search projects..."
            className="h-14 w-full rounded-[22px] border border-white/10 bg-[#202020] pl-12 pr-4 text-sm tracking-[-0.02em] text-zinc-100 outline-none transition placeholder:text-zinc-500 focus:border-zinc-500"
          />
        </label>

        <div className="flex items-center justify-end gap-3 text-sm text-zinc-500">
          <span>Sort by</span>
          <div className="inline-flex items-center gap-2 rounded-[18px] border border-white/10 bg-[#202020] px-4 py-2.5 text-zinc-100">
            <span>Activity</span>
            <ChevronDown size={16} strokeWidth={1.8} className="text-zinc-500" />
          </div>
        </div>
      </section>

      {notice ? (
        <section className="rounded-2xl border border-emerald-400/15 bg-emerald-500/10 px-4 py-4 text-sm text-emerald-100">
          {notice}
        </section>
      ) : null}

      {error ? (
        <section className="rounded-3xl border border-rose-400/20 bg-rose-500/10 p-5 text-sm text-rose-100">
          {error}
        </section>
      ) : loading ? (
        <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div
              key={index}
              className="h-52 animate-pulse rounded-[26px] border border-white/8 bg-[#212121]"
            />
          ))}
        </section>
      ) : filteredProjects.length ? (
        <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {filteredProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              menuOpen={openMenuId === project.id}
              deleting={deletingProjectId === project.id}
              onToggleMenu={(projectId) =>
                setOpenMenuId((current) => (current === projectId ? null : projectId))
              }
              onCloseMenu={() => setOpenMenuId(null)}
              onArchive={(projectName) =>
                setNotice(`“${projectName}” 的归档功能稍后接入，这次先补齐真实删除。`)
              }
              onDelete={(targetProject) => void handleDeleteProject(targetProject)}
            />
          ))}
        </section>
      ) : (
        <section className="rounded-3xl border border-dashed border-white/10 bg-[#1d1d1d] px-6 py-10 text-sm leading-7 text-zinc-500">
          没有找到匹配的项目。可以调整关键词，或者直接创建新的项目工作区。
        </section>
      )}
    </AppShell>
  );
}

function ProjectCard({
  project,
  menuOpen,
  deleting,
  onToggleMenu,
  onCloseMenu,
  onArchive,
  onDelete,
}: ProjectCardProps) {
  const menuRef = useRef<HTMLDivElement | null>(null);
  const description =
    project.description?.trim() ||
    `以 ${project.default_language.toUpperCase()} 为主语言的写作项目，可继续进入详情查看书籍、章节与场景结构。`;

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onCloseMenu();
      }
    }

    if (menuOpen) {
      window.addEventListener("mousedown", handlePointerDown);
    }

    return () => {
      window.removeEventListener("mousedown", handlePointerDown);
    };
  }, [menuOpen, onCloseMenu]);

  const actions: CardAction[] = [
    { href: `/project/${project.id}`, label: "查看项目", icon: Eye },
    { href: `/editor?projectId=${project.id}`, label: "写作编辑", icon: PencilLine },
    { href: `/lore?projectId=${project.id}`, label: "设定资料", icon: BookOpenText },
    {
      label: "归档项目",
      icon: Archive,
      onClick: () => onArchive(project.name),
    },
    {
      label: deleting ? "删除中..." : "删除项目",
      icon: Trash2,
      destructive: true,
      disabled: deleting,
      onClick: () => onDelete(project),
    },
  ];

  return (
    <article className="group relative flex min-h-[220px] flex-col rounded-[26px] border border-white/8 bg-[#212121] p-5 transition hover:border-zinc-700 hover:bg-[#242424]">
      <Link
        href={`/project/${project.id}`}
        className="absolute inset-0 rounded-[26px]"
        aria-label={`打开项目 ${project.name}`}
      />

      <div className="pointer-events-none relative z-10 pr-12">
        <h2 className="text-lg font-medium tracking-[-0.03em] text-zinc-100">{project.name}</h2>
        <p className="mt-2 line-clamp-2 text-sm leading-7 text-zinc-500">{description}</p>
      </div>

      <div className="pointer-events-none relative z-10 mt-auto flex items-end justify-between gap-4 pt-8">
        <div className="text-xs tracking-[0.01em] text-zinc-600">
          {formatUpdatedAt(project.updated_at)}
        </div>
        <div className="rounded-full border border-white/8 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-zinc-500">
          {project.genre || project.default_language}
        </div>
      </div>

      <div ref={menuRef} className="absolute right-4 top-4 z-20">
        <button
          type="button"
          aria-label={`展开 ${project.name} 菜单`}
          onClick={(event) => {
            event.stopPropagation();
            onToggleMenu(project.id);
          }}
          className={`rounded-xl p-2 text-zinc-500 transition ${
            menuOpen
              ? "bg-[#171717] text-zinc-100"
              : "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 hover:bg-white/5 hover:text-zinc-100"
          }`}
        >
          <MoreVertical size={17} strokeWidth={1.8} />
        </button>

        {menuOpen ? (
          <div
            className="absolute right-0 top-12 w-52 rounded-[24px] border border-white/8 bg-[#2a2a2a] p-2 shadow-[0_16px_48px_rgba(0,0,0,0.35)]"
            onClick={(event) => event.stopPropagation()}
          >
            {actions.map((action) => {
              const Icon = action.icon;
              const sharedClass = `flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm transition ${
                action.destructive
                  ? "text-rose-300 hover:bg-rose-500/10"
                  : "text-zinc-200 hover:bg-white/5"
              }`;

              if (isLinkAction(action)) {
                return (
                  <Link
                    key={action.label}
                    href={action.href}
                    className={sharedClass}
                    onClick={onCloseMenu}
                  >
                    <Icon size={16} strokeWidth={1.8} />
                    <span>{action.label}</span>
                  </Link>
                );
              }

              return (
                <button
                  key={action.label}
                  type="button"
                  disabled={action.disabled}
                  className={`${sharedClass} disabled:cursor-not-allowed disabled:opacity-50`}
                  onClick={() => {
                    action.onClick();
                    onCloseMenu();
                  }}
                >
                  <Icon size={16} strokeWidth={1.8} />
                  <span>{action.label}</span>
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function formatUpdatedAt(value: string) {
  const target = new Date(value);
  const diff = Date.now() - target.getTime();
  const day = 24 * 60 * 60 * 1000;

  if (Number.isNaN(target.getTime())) {
    return "最近更新";
  }

  if (diff < day) {
    const hours = Math.max(1, Math.floor(diff / (60 * 60 * 1000)));
    return `${hours} 小时前更新`;
  }

  const days = Math.floor(diff / day);
  if (days < 30) {
    return `${days} 天前更新`;
  }

  return `${target.toLocaleDateString("zh-CN")} 更新`;
}
