"use client";

import { api } from "@/services/api";
import { useApiQuery } from "@/hooks/useApiQuery";
import { Card, CardBody } from "@/components/shared/Card";
import EmptyState from "@/components/shared/EmptyState";
import Badge from "@/components/shared/Badge";
import Skeleton from "@/components/shared/Skeleton";
import { formatCurrency, formatDate } from "@/lib/utils";

const statusTone = {
  delivered: "success",
  shipped: "info",
  cancelled: "danger",
  returned: "warning",
};

export default function OrdersTable() {
  const { data, error, loading } = useApiQuery(() => api.listOrders());
  const orders = data?.items || [];

  if (loading) {
    return <Skeleton className="h-64 w-full rounded-xl" />;
  }

  if (error) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-red-600">{error.message}</p>
        </CardBody>
      </Card>
    );
  }

  if (!orders.length) {
    return (
      <EmptyState
        title="No orders found"
        description="Orders are scoped to your ResolveAI customer profile. Run backend seed scripts to load demo data."
      />
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-zinc-200 text-sm">
          <thead className="bg-zinc-50 text-left text-xs font-semibold uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="px-4 py-3">Reference</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Payment</th>
              <th className="px-4 py-3">Total</th>
              <th className="px-4 py-3">Ordered</th>
              <th className="px-4 py-3">Products</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 bg-white">
            {orders.map((order) => (
              <tr key={order.id} className="hover:bg-zinc-50/80">
                <td className="px-4 py-3 font-medium text-zinc-900">
                  {order.order_reference}
                </td>
                <td className="px-4 py-3">
                  <Badge tone={statusTone[order.order_status] || "default"}>
                    {order.order_status}
                  </Badge>
                </td>
                <td className="px-4 py-3 capitalize text-zinc-700">
                  {order.payment_status}
                </td>
                <td className="px-4 py-3 font-medium text-zinc-900">
                  {formatCurrency(order.total_amount, order.currency)}
                </td>
                <td className="px-4 py-3 text-zinc-600">
                  {formatDate(order.ordered_at)}
                </td>
                <td className="max-w-xs truncate px-4 py-3 text-zinc-600">
                  {order.product_summary || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}