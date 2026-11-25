"use client";

import {
  BarChart3,
  Bot,
  ClipboardCheck,
  LayoutDashboard,
  Settings,
  Ticket,
} from "lucide-react";
import AppShell from "@/components/shared/AppShell";
import RoleGuard from "@/components/shared/RoleGuard";

const navItems = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/approvals", label: "Approvals", icon: ClipboardCheck },
  { href: "/admin/tickets", label: "Tickets", icon: Ticket },
  { href: "/admin/agent-runs", label: "Agent runs", icon: Bot },
  { href: "/admin/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/admin/settings", label: "Settings", icon: Settings },
];

const STAFF_ROLES = ["support_agent", "admin"];

export default function AdminLayout({ children }) {
  return (
    <RoleGuard allowedRoles={STAFF_ROLES}>
      <AppShell brand="ResolveAI Admin" navItems={navItems}>
        {children}
      </AppShell>
    </RoleGuard>
  );
}