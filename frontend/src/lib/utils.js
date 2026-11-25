import clsx from "clsx";

export function cn(...inputs) {
  return clsx(inputs);
}

export function homeForRole(role) {
  if (role === "admin" || role === "support_agent") return "/admin";
  return "/customer";
}

export function isStaffRole(role) {
  return role === "admin" || role === "support_agent";
}

export function formatCurrency(amount, currency = "USD") {
  if (amount == null || Number.isNaN(Number(amount))) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(Number(amount));
}

export function formatDate(value) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return String(value);
  }
}