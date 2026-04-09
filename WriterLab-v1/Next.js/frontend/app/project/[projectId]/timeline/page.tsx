import TimelineLibraryPage from "@/features/timeline/timeline-library-page";

export default async function ProjectTimelinePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;

  return <TimelineLibraryPage projectId={projectId} />;
}
