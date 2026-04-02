import type { ReactNode } from "react";

type InfoCardProps = {
  title: string;
  description?: string;
  children: ReactNode;
  tone?: "default" | "amber" | "sky" | "emerald";
};

const toneClassMap = {
  default: "border-white/8 bg-[#212121]",
  amber: "border-amber-400/15 bg-amber-500/8",
  sky: "border-sky-400/15 bg-sky-500/8",
  emerald: "border-emerald-400/15 bg-emerald-500/8",
} as const;

export function InfoCard({
  title,
  description,
  children,
  tone = "default",
}: InfoCardProps) {
  return (
    <section className={`rounded-[28px] border p-5 ${toneClassMap[tone]}`}>
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold tracking-[-0.02em] text-zinc-100">{title}</h2>
        {description ? (
          <p className="text-sm leading-7 text-zinc-500">{description}</p>
        ) : null}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}
