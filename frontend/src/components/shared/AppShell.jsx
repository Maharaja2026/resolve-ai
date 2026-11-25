"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Menu, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import DemoBanner from "@/components/shared/DemoBanner";
import Button from "@/components/shared/Button";
import { cn } from "@/lib/utils";

export default function AppShell({ brand, navItems, children }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, profile, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      toast.success("Signed out");
      router.replace("/login");
    } catch (err) {
      toast.error(err.message || "Could not sign out");
    }
  };

  const NavLinks = ({ onNavigate }) =>
    navItems.map((item) => {
      const active =
        pathname === item.href ||
        (item.href !== "/" &&
          item.href !== "/customer" &&
          item.href !== "/admin" &&
          pathname.startsWith(`${item.href}/`));
      const Icon = item.icon;
      return (
        <Link
          key={item.href}
          href={item.href}
          onClick={onNavigate}
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
            active
              ? "bg-teal-50 text-teal-800"
              : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900",
          )}
        >
          <Icon className="h-4 w-4 shrink-0" aria-hidden />
          {item.label}
        </Link>
      );
    });

  return (
    <div className="min-h-screen bg-zinc-50">
      <DemoBanner />
      <div className="flex min-h-[calc(100vh-41px)]">
        <aside className="hidden w-64 shrink-0 border-r border-zinc-200 bg-white lg:block">
          <div className="flex h-16 items-center border-b border-zinc-100 px-5">
            <Link
              href={navItems[0]?.href || "/"}
              className="text-lg font-bold text-zinc-900"
            >
              {brand}
            </Link>
          </div>
          <nav className="space-y-1 p-3">
            <NavLinks />
          </nav>
        </aside>

        {mobileOpen ? (
          <motion className="fixed inset-0 z-40 lg:hidden">
            <button
              type="button"
              className="absolute inset-0 bg-black/40"
              aria-label="Close menu overlay"
              onClick={() => setMobileOpen(false)}
            />
            <div className="absolute left-0 top-0 flex h-full w-72 flex-col bg-white shadow-xl">
              <div className="flex h-16 items-center justify-between border-b border-zinc-100 px-4">
                <span className="font-bold text-zinc-900">{brand}</span>
                <button
                  type="button"
                  className="rounded-lg p-2 text-zinc-600 hover:bg-zinc-100"
                  onClick={() => setMobileOpen(false)}
                  aria-label="Close menu"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              <nav className="space-y-1 p-3">
                <NavLinks onNavigate={() => setMobileOpen(false)} />
              </nav>
            </div>
          </motion>
        ) : null}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-zinc-200 bg-white/95 px-4 backdrop-blur sm:px-6">
            <motion className="flex items-center gap-3">
              <button
                type="button"
                className="rounded-lg p-2 text-zinc-600 hover:bg-zinc-100 lg:hidden"
                onClick={() => setMobileOpen(true)}
                aria-label="Open menu"
              >
                <Menu className="h-5 w-5" />
              </button>
              <span className="text-sm font-semibold text-teal-700 lg:hidden">
                {brand}
              </span>
            </motion>
            <motion className="flex items-center gap-3">
              <motion className="hidden text-right sm:block">
                <p className="text-sm font-medium text-zinc-900">
                  {profile?.profile?.full_name || user?.email || "User"}
                </p>
                <p className="text-xs capitalize text-zinc-500">
                  {profile?.role || "customer"}
                </p>
              </motion>
              <Button variant="ghost" onClick={handleLogout} className="px-2">
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Sign out</span>
              </Button>
            </motion>
          </header>
          <main className="flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
        </div>
      </div>
    </div>
  );
}

function motion({ children, className }) {
  return <div className={className}>{children}</div>;
}