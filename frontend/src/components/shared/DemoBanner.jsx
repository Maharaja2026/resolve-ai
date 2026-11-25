import { AlertTriangle } from "lucide-react";

export default function DemoBanner() {
  return (
    <div
      role="status"
      className="flex items-center justify-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-sm font-medium text-amber-950"
    >
      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" aria-hidden />
      <span>
        DEMO ENVIRONMENT — All order, refund, cancellation, and shipping
        operations are simulated.
      </span>
    </div>
  );
}