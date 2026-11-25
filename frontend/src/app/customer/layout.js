"use client";

import {
  LayoutDashboard,
  MessageSquare,
  Package,
  Ticket,
} from "lucide-react";
import AppShell from "@/components/shared/AppShell";
import RoleGuard from "@/components/shared/RoleGuard";

const navItems = [
  { href: "/customer", label: "Dashboard", icon: LayoutDashboard },
  { href: "/customer/orders", label: "Orders", icon: Package },
  { href: "/customer/chat", label: "Chat", icon: MessageSquare },
  { href: "/customer/tickets", label: "Tickets", icon: Ticket },
];

const CUSTOMER_ROLES = ["customer"];

export default function CustomerLayout({ children }) {
  return (
    <RoleGuard allowedRoles={CUSTOMER_ROLES}>
      <AppShell brand="ResolveAI" navItems={navItems}>
        {children}
      </AppShell>
    </RoleGuard>
  );
}