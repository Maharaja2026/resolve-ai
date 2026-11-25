"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { homeForRole } from "@/lib/utils";
import Skeleton from "@/components/shared/Skeleton";

export default function RoleGuard({ children, allowedRoles }) {
  const { loading, profileLoading, isAuthenticated, role, profile } = useAuth();
  const router = useRouter();

  // Only block the shell on the first auth/profile load — never on tab focus
  // token refresh / background profile refresh.
  const initialBusy = loading || (isAuthenticated && !profile && profileLoading);
  const hasAccess =
    isAuthenticated && (!allowedRoles || allowedRoles.includes(role));

  useEffect(() => {
    if (loading || (isAuthenticated && !profile && profileLoading)) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    if (allowedRoles && !allowedRoles.includes(role)) {
      router.replace(homeForRole(role));
    }
  }, [loading, profileLoading, isAuthenticated, profile, role, allowedRoles, router]);

  if (initialBusy) {
    return (
      <div className="space-y-3 p-8">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    );
  }

  if (!hasAccess) {
    return null;
  }

  return children;
}
