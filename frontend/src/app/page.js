"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { homeForRole } from "@/lib/utils";
import Skeleton from "@/components/shared/Skeleton";

export default function HomePage() {
  const { loading, profileLoading, isAuthenticated, role } = useAuth();
  const router = useRouter();
  const busy = loading || profileLoading;

  useEffect(() => {
    if (busy) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    router.replace(homeForRole(role));
  }, [busy, isAuthenticated, role, router]);

  return (
    <motion className="flex min-h-screen items-center justify-center bg-zinc-50 p-8">
      <motion className="w-full max-w-md space-y-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full" />
      </motion>
    </motion>
  );
}

function motion({ children, className }) {
  return <div className={className}>{children}</div>;
}