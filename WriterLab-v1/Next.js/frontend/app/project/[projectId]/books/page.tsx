import ProjectDetail from "@/features/project/project-detail";

export default async function ProjectBooksPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;

  return <ProjectDetail projectId={projectId} />;
}
