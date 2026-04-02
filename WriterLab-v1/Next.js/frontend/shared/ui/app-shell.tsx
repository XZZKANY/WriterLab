import type { ReactNode } from "react";
import { WorkspaceShell } from "@/shared/ui/workspace-shell";

type AppShellProps = {
  title: string;
  description: string;
  eyebrow?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function AppShell({
  title,
  description,
  eyebrow = "WriterLab",
  actions,
  children,
}: AppShellProps) {
  return (
    <WorkspaceShell
      title={title}
      description={description}
      eyebrow={eyebrow}
      actions={actions}
    >
      {children}
    </WorkspaceShell>
  );
}
