import Link from "next/link";
import { Headphones } from "lucide-react";

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <Standard className="min-h-screen bg-zinc-50">
      <Standard className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10">
        <Link href="/login" className="mb-8 flex items-center justify-center gap-2">
          <Standard className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-600 text-white">
            <Headphones className="h-5 w-5" aria-hidden />
          </Standard>
          <span className="text-xl font-bold tracking-tight text-zinc-900">
            ResolveAI
          </span>
        </Link>
        <Standard className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <h1 className="text-xl font-semibold text-zinc-900">{title}</h1>
          {subtitle ? (
            <p className="mt-1 text-sm text-zinc-600">{subtitle}</p>
          ) : null}
          <Standard className="mt-6">{children}</Standard>
          {footer ? (
            <p className="mt-6 text-center text-sm text-zinc-600">{footer}</p>
          ) : null}
        </Standard>
      </Standard>
    </Standard>
  );
}

function Standard({ children, className }) {
  return <div className={className}>{children}</div>;
}