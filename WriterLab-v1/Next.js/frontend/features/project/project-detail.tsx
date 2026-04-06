"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  BookOpenText,
  BookText,
  LayoutDashboard,
  PencilLine,
  ScrollText,
  Shapes,
} from "lucide-react";
import {
  fetchProjectOverview,
  type ProjectBookSummary,
  type ProjectChapterSummary,
  type ProjectOverviewResponse,
  type ProjectResponse,
  type ProjectSceneSummary,
} from "@/lib/api/projects";
import { AppShell } from "@/shared/ui/app-shell";
import { InfoCard } from "@/shared/ui/info-card";

type Project = ProjectResponse;
type Book = ProjectBookSummary;
type Chapter = ProjectChapterSummary;
type Scene = ProjectSceneSummary;

type ProjectDetailProps = {
  projectId: string;
};

type WorkbenchLink = {
  href: string;
  label: string;
  description: string;
  icon: typeof LayoutDashboard;
  tone: "default" | "amber" | "sky" | "emerald";
};

const toneClassMap = {
  default: "border-white/8 bg-[#1d1d1d] text-zinc-200 hover:border-zinc-600 hover:bg-[#242424]",
  amber: "border-amber-400/15 bg-amber-500/8 text-amber-100 hover:border-amber-300/30 hover:bg-amber-500/12",
  sky: "border-sky-400/15 bg-sky-500/8 text-sky-100 hover:border-sky-300/30 hover:bg-sky-500/12",
  emerald:
    "border-emerald-400/15 bg-emerald-500/8 text-emerald-100 hover:border-emerald-300/30 hover:bg-emerald-500/12",
} as const;

export default function ProjectDetail({ projectId }: ProjectDetailProps) {
  const [project, setProject] = useState<Project | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [chaptersByBook, setChaptersByBook] = useState<Record<string, Chapter[]>>({});
  const [scenesByChapter, setScenesByChapter] = useState<Record<string, Scene[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!projectId) {
        setProject(null);
        setBooks([]);
        setChaptersByBook({});
        setScenesByChapter({});
        setError("项目标识缺失，无法读取详情。");
        setLoading(false);
        return;
      }

      try {
        const overview = await fetchProjectOverview<ProjectOverviewResponse>(projectId);

        if (!cancelled) {
          setProject(overview.project);
          setBooks(overview.books);
          setChaptersByBook(overview.chapters_by_book);
          setScenesByChapter(overview.scenes_by_chapter);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "读取项目详情失败");
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
  }, [projectId]);

  const chapterCount = useMemo(
    () => Object.values(chaptersByBook).reduce((sum, items) => sum + items.length, 0),
    [chaptersByBook],
  );
  const sceneCount = useMemo(
    () => Object.values(scenesByChapter).reduce((sum, items) => sum + items.length, 0),
    [scenesByChapter],
  );

  const workbenchLinks: WorkbenchLink[] = [
    {
      href: `/project/${projectId}`,
      label: "项目概览",
      description: "回到当前项目总览，查看结构摘要与最近内容。",
      icon: LayoutDashboard,
      tone: "default",
    },
    {
      href: `/editor?projectId=${projectId}`,
      label: "写作编辑",
      description: "进入写作台，继续正文创作与场景修订。",
      icon: PencilLine,
      tone: "amber",
    },
    {
      href: `/lore?projectId=${projectId}`,
      label: "设定资料",
      description: "从当前项目上下文直接查看角色、地点与词条。",
      icon: BookOpenText,
      tone: "sky",
    },
    {
      href: `/project/${projectId}/books`,
      label: "书籍目录",
      description: "浏览项目内书籍结构与摘要。",
      icon: BookText,
      tone: "default",
    },
    {
      href: `/project/${projectId}/chapters`,
      label: "章节浏览",
      description: "按章节粒度查看内容骨架与进度。",
      icon: ScrollText,
      tone: "default",
    },
    {
      href: `/project/${projectId}/scenes`,
      label: "场景浏览",
      description: "快速定位到场景层并跳转后续编辑。",
      icon: Shapes,
      tone: "emerald",
    },
  ];

  return (
    <AppShell
      title={project?.name || "项目详情"}
      description={
        project?.description ||
        "这里整合项目、书籍、章节与场景浏览能力，并把写作编辑与设定资料收束到具体项目内。"
      }
      actions={
        <>
          <Link
            href="/project"
            className="rounded-xl border border-white/8 bg-[#212121] px-4 py-2 text-sm text-zinc-200 transition hover:border-zinc-600 hover:bg-[#262626]"
          >
            返回项目列表
          </Link>
          <Link
            href={`/editor?projectId=${projectId}`}
            className="rounded-xl bg-zinc-100 px-4 py-2 text-sm font-medium text-black transition hover:bg-zinc-200"
          >
            进入写作编辑
          </Link>
        </>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[0.82fr_1.38fr]">
        <div className="space-y-6">
          <InfoCard
            title="写作台功能"
            description="写作编辑、设定资料和内容浏览都从当前项目里展开，不再散落在全局侧栏。"
          >
            <div className="space-y-3">
              {workbenchLinks.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    className={`flex items-start gap-3 rounded-[24px] border px-4 py-4 transition ${toneClassMap[item.tone]}`}
                  >
                    <span className="mt-0.5 rounded-xl border border-white/8 bg-[#171717] p-2 text-zinc-100">
                      <Icon size={16} strokeWidth={1.8} />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-medium tracking-[-0.02em]">{item.label}</span>
                      <span className="mt-1 block text-sm leading-6 text-zinc-400">
                        {item.description}
                      </span>
                    </span>
                  </Link>
                );
              })}
            </div>
          </InfoCard>

          <InfoCard title="项目速览" description="项目内工作台左侧保留必要元信息，方便快速确认上下文。">
            {loading ? (
              <div className="text-sm text-zinc-500">正在整理项目元信息…</div>
            ) : error ? (
              <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-4 text-sm text-rose-100">
                {error}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="rounded-2xl border border-white/8 bg-[#1d1d1d] px-4 py-4">
                  <div className="text-xs text-zinc-500">项目名称</div>
                  <div className="mt-2 text-lg font-semibold text-zinc-100">{project?.name || "未命名项目"}</div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/8 bg-[#1d1d1d] px-4 py-4">
                    <div className="text-xs text-zinc-500">题材</div>
                    <div className="mt-2 text-sm text-zinc-200">{project?.genre || "未设置"}</div>
                  </div>
                  <div className="rounded-2xl border border-white/8 bg-[#1d1d1d] px-4 py-4">
                    <div className="text-xs text-zinc-500">默认语言</div>
                    <div className="mt-2 text-sm uppercase text-zinc-200">
                      {project?.default_language || "未设置"}
                    </div>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl border border-amber-400/15 bg-amber-500/8 px-4 py-4">
                    <div className="text-xs text-amber-300">书籍</div>
                    <div className="mt-2 text-2xl font-semibold text-zinc-100">{books.length}</div>
                  </div>
                  <div className="rounded-2xl border border-sky-400/15 bg-sky-500/8 px-4 py-4">
                    <div className="text-xs text-sky-300">章节</div>
                    <div className="mt-2 text-2xl font-semibold text-zinc-100">{chapterCount}</div>
                  </div>
                  <div className="rounded-2xl border border-emerald-400/15 bg-emerald-500/8 px-4 py-4">
                    <div className="text-xs text-emerald-300">场景</div>
                    <div className="mt-2 text-2xl font-semibold text-zinc-100">{sceneCount}</div>
                  </div>
                </div>
              </div>
            )}
          </InfoCard>
        </div>

        <div className="space-y-6">
          <InfoCard title="结构摘要" description="项目详情页直接串起 books / chapters / scenes 三级资源。">
            {loading ? (
              <div className="text-sm text-zinc-500">正在汇总项目结构…</div>
            ) : error ? (
              <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-4 text-sm text-rose-100">
                {error}
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl border border-amber-400/15 bg-amber-500/8 px-4 py-4">
                  <div className="text-xs text-amber-300">书籍</div>
                  <div className="mt-2 text-2xl font-semibold text-zinc-100">{books.length}</div>
                </div>
                <div className="rounded-2xl border border-sky-400/15 bg-sky-500/8 px-4 py-4">
                  <div className="text-xs text-sky-300">章节</div>
                  <div className="mt-2 text-2xl font-semibold text-zinc-100">{chapterCount}</div>
                </div>
                <div className="rounded-2xl border border-emerald-400/15 bg-emerald-500/8 px-4 py-4">
                  <div className="text-xs text-emerald-300">场景</div>
                  <div className="mt-2 text-2xl font-semibold text-zinc-100">{sceneCount}</div>
                </div>
              </div>
            )}
          </InfoCard>

          <InfoCard title="书籍与章节" description="优先提供浏览与定位能力，为后续更细的编辑子路由留出空间。">
            {loading ? (
              <div className="text-sm text-zinc-500">正在读取书籍、章节和场景…</div>
            ) : error ? (
              <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-4 text-sm text-rose-100">
                {error}
              </div>
            ) : books.length ? (
              <div className="space-y-5">
                {books.map((book) => (
                  <article
                    key={book.id}
                    className="rounded-[24px] border border-white/8 bg-[#1d1d1d] px-5 py-5"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h2 className="text-lg font-semibold text-zinc-100">{book.title}</h2>
                        <p className="mt-2 text-sm leading-7 text-zinc-500">
                          {book.summary || "暂无书籍摘要。"}
                        </p>
                      </div>
                      <span className="rounded-full border border-white/8 bg-[#171717] px-3 py-1 text-xs text-zinc-400">
                        {book.status}
                      </span>
                    </div>

                    <div className="mt-4 space-y-3">
                      {(chaptersByBook[book.id] ?? []).map((chapter) => (
                        <div
                          key={chapter.id}
                          className="rounded-2xl border border-white/8 bg-[#212121] px-4 py-4"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <div className="text-sm font-semibold text-zinc-100">
                                第 {chapter.chapter_no} 章 · {chapter.title}
                              </div>
                              <div className="mt-1 text-sm text-zinc-500">
                                {chapter.summary || "暂无章节摘要。"}
                              </div>
                            </div>
                            <span className="rounded-full border border-white/8 bg-[#171717] px-3 py-1 text-xs text-zinc-500">
                              {chapter.status}
                            </span>
                          </div>

                          <div className="mt-3 flex flex-wrap gap-2 text-xs text-zinc-500">
                            {(scenesByChapter[chapter.id] ?? []).map((scene) => (
                              <Link
                                key={scene.id}
                                href={`/editor?projectId=${projectId}&scene_id=${scene.id}`}
                                className="rounded-full border border-white/8 bg-[#171717] px-3 py-1.5 transition hover:border-zinc-600 hover:bg-[#262626]"
                              >
                                第 {scene.scene_no} 场 · {scene.title || "未命名场景"}
                              </Link>
                            ))}
                            {(scenesByChapter[chapter.id] ?? []).length === 0 ? (
                              <span>暂无场景。</span>
                            ) : null}
                          </div>
                        </div>
                      ))}

                      {(chaptersByBook[book.id] ?? []).length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-white/10 bg-[#1a1a1a] px-4 py-5 text-sm text-zinc-500">
                          这本书还没有章节数据。
                        </div>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-white/10 bg-[#1a1a1a] px-4 py-8 text-sm text-zinc-500">
                该项目暂时还没有书籍数据。
              </div>
            )}
          </InfoCard>
        </div>
      </div>
    </AppShell>
  );
}
