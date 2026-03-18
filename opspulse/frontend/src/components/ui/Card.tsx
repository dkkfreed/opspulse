import { cn } from "@/lib/utils";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  glowColor?: "cyan" | "amber" | "red" | "green" | "purple" | "none";
}

export function Card({ children, className, glowColor = "none" }: CardProps) {
  const glowMap = {
    cyan: "shadow-[0_0_20px_rgba(0,212,255,0.07)] border-accent-cyan/20",
    amber: "shadow-[0_0_20px_rgba(255,179,64,0.07)] border-accent-amber/20",
    red: "shadow-[0_0_20px_rgba(255,71,87,0.07)] border-accent-red/20",
    green: "shadow-[0_0_20px_rgba(0,230,118,0.07)] border-accent-green/20",
    purple: "shadow-[0_0_20px_rgba(176,133,255,0.07)] border-accent-purple/20",
    none: "border-bg-border",
  };

  return (
    <div className={cn(
      "bg-bg-card rounded-xl border p-5 animate-slide-up",
      glowMap[glowColor],
      className
    )}>
      {children}
    </div>
  );
}
