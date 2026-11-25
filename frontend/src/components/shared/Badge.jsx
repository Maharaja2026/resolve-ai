import { cn } from "@/lib/utils";

const tones = {
  default: "bg-zinc-100 text-zinc-700",
  success: "bg-emerald-50 text-emerald-700",
  warning: "bg-amber-50 text-amber-800",
  danger: "bg-red-50 text-red-700",
  info: "bg-teal-50 text-teal-800",
};

export default function Badge({ children, tone = "default", className }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium capitalize",
        tones[tone] || tones.default,
        className,
      )}
    >
      {children}
    </span>
  );
}