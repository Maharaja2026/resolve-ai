"use client";

import { MessageSquare, Package, Ticket } from "lucide-react";
import { api } from "@/services/api";
import { useApiQuery } from "@/hooks/useApiQuery";
import StatGrid from "@/components/dashboard/StatGrid";
import { Card, CardBody, CardHeader } from "@/components/shared/Card";
import EmptyState from "@/components/shared/EmptyState";
import Badge from "@/components/shared/Badge";
import { formatCurrency, formatDate } from "@/lib/utils";
import Link from "next/link";
import Button from "@/components/shared/Button";

export default function CustomerDashboard() {
  const ordersQuery = useApiQuery(() => api.listOrders());
  const ticketsQuery = useApiQuery(() => api.listTickets());
  const conversationsQuery = useApiQuery(() => api.listConversations());

  const loading =
    ordersQuery.loading || ticketsQuery.loading || conversationsQuery.loading;

  const orders = ordersQuery.data?.items || [];
  const tickets = ticketsQuery.data || [];
  const conversations = conversationsQuery.data || [];

  const openTickets = tickets.filter((t) =>
    ["open", "in_progress", "escalated"].includes(t.status),
  ).length;

  const stats = [
    {
      label: "Orders",
      value: ordersQuery.data?.total ?? orders.length,
      icon: Package,
      hint: "Linked to your customer profile",
    },
    {
      label: "Open tickets",
      value: openTickets,
      icon: Ticket,
    },
    {
      label: "Conversations",
      value: conversations.length,
      icon: MessageSquare,
    },
    {
      label: "Recent order value",
      value: orders[0]
        ? formatCurrency(orders[0].total_amount, orders[0].currency)
        : "—",
      icon: Package,
      hint: orders[0]?.order_reference,
    },
  ];

  return (
    <Standard className="space-y-6">
      <StatGrid stats={stats} loading={loading} />

      <Standard className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <Standard className="flex items-center justify-between gap-2">
              <h2 className="font-semibold text-zinc-900">Recent orders</h2>
              <Link href="/customer/orders">
                <Button variant="ghost" className="py-1 text-teal-700">
                  View all
                </Button>
              </Link>
            </Standard>
          </CardHeader>
          <CardBody className="space-y-3">
            {ordersQuery.error ? (
              <p className="text-sm text-red-600">{ordersQuery.error.message}</p>
            ) : null}
            {!loading && orders.length === 0 ? (
              <EmptyState
                title="No orders yet"
                description="Demo orders appear after your customer profile is seeded in the backend."
              />
            ) : null}
            {orders.slice(0, 5).map((order) => (
              <Standard
                key={order.id}
                className="flex items-center justify-between rounded-lg border border-zinc-100 px-3 py-2"
              >
                <Standard>
                  <p className="text-sm font-medium text-zinc-900">
                    {order.order_reference}
                  </p>
                  <p className="text-xs text-zinc-500">
                    {formatDate(order.ordered_at)}
                  </p>
                </Standard>
                <Standard className="text-right">
                  <Badge tone="info">{order.order_status}</Badge>
                  <p className="mt-1 text-sm font-medium text-zinc-800">
                    {formatCurrency(order.total_amount, order.currency)}
                  </p>
                </Standard>
              </Standard>
            ))}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <Standard className="flex items-center justify-between gap-2">
              <h2 className="font-semibold text-zinc-900">Support tickets</h2>
              <Link href="/customer/tickets">
                <Button variant="ghost" className="py-1 text-teal-700">
                  View all
                </Button>
              </Link>
            </Standard>
          </CardHeader>
          <CardBody className="space-y-3">
            {ticketsQuery.error ? (
              <p className="text-sm text-red-600">{ticketsQuery.error.message}</p>
            ) : null}
            {!loading && tickets.length === 0 ? (
              <EmptyState
                title="No tickets"
                description="Open a conversation with ResolveAI to create support tickets automatically."
                action={
                  <Link href="/customer/chat">
                    <Button>Start chat</Button>
                  </Link>
                }
              />
            ) : null}
            {tickets.slice(0, 5).map((ticket) => (
              <Standard
                key={ticket.id}
                className="flex items-center justify-between rounded-lg border border-zinc-100 px-3 py-2"
              >
                <Standard>
                  <p className="text-sm font-medium text-zinc-900">
                    {ticket.subject || `Ticket ${ticket.id.slice(0, 8)}`}
                  </p>
                  <p className="text-xs text-zinc-500">
                    {formatDate(ticket.created_at)}
                  </p>
                </Standard>
                <Badge
                  tone={
                    ticket.status === "resolved"
                      ? "success"
                      : ticket.priority === "high"
                        ? "danger"
                        : "warning"
                  }
                >
                  {ticket.status}
                </Badge>
              </Standard>
            ))}
          </CardBody>
        </Card>
      </Standard>
    </Standard>
  );
}

function Standard({ children, className }) {
  return <div className={className}>{children}</div>;
}