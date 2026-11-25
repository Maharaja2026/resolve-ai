"use client";

import { api } from "@/services/api";
import { useApiQuery } from "@/hooks/useApiQuery";
import { Card, CardBody } from "@/components/shared/Card";
import EmptyState from "@/components/shared/EmptyState";
import Badge from "@/components/shared/Badge";
import Skeleton from "@/components/shared/Skeleton";
import { formatDate } from "@/lib/utils";

export default function TicketsTable({ staff = false }) {
  const { data, error, loading } = useApiQuery(() => api.listTickets());
  const tickets = data || [];

  if (loading) return <Skeleton className="h-64 w-full rounded-xl" />;

  if (error) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-red-600">{error.message}</p>
        </CardBody>
      </Card>
    );
  }

  if (!tickets.length) {
    return (
      <EmptyState
        title="No tickets"
        description={
          staff
            ? "Tickets created by the agent or customers will appear here."
            : "Your support tickets will show up once created via chat or escalation."
        }
      />
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-zinc-200 text-sm">
          <thead className="bg-zinc-50 text-left text-xs font-semibold uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="px-4 py-3">Subject</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">Created</th>
              {staff ? <th className="px-4 py-3">Customer</th> : null}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 bg-white">
            {tickets.map((ticket) => (
              <tr key={ticket.id} className="hover:bg-zinc-50/80">
                <td className="px-4 py-3 font-medium text-zinc-900">
                  {ticket.subject || `Ticket ${ticket.id.slice(0, 8)}`}
                </td>
                <td className="px-4 py-3">
                  <Badge
                    tone={
                      ticket.status === "resolved"
                        ? "success"
                        : ticket.status === "escalated"
                          ? "danger"
                          : "warning"
                    }
                  >
                    {ticket.status}
                  </Badge>
                </td>
                <td className="px-4 py-3 capitalize text-zinc-700">
                  {ticket.priority || "normal"}
                </td>
                <td className="px-4 py-3 text-zinc-600">
                  {formatDate(ticket.created_at)}
                </td>
                {staff ? (
                  <td className="px-4 py-3 font-mono text-xs text-zinc-500">
                    {ticket.customer_id?.slice(0, 8) || "—"}
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}