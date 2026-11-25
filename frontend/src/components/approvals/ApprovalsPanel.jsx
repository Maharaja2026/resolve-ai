"use client";

import { useState } from "react";
import { Check, X } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/services/api";
import { useApiQuery } from "@/hooks/useApiQuery";
import { Card, CardBody } from "@/components/shared/Card";
import Button from "@/components/shared/Button";
import Badge from "@/components/shared/Badge";
import EmptyState from "@/components/shared/EmptyState";
import Skeleton from "@/components/shared/Skeleton";
import { formatDate } from "@/lib/utils";

export default function ApprovalsPanel() {
  const { data, error, loading, reload } = useApiQuery(() => api.listApprovals());
  const [busyId, setBusyId] = useState(null);

  const items = Array.isArray(data) ? data : [];

  const review = async (id, action) => {
    setBusyId(id);
    try {
      if (action === "approve") {
        await api.approveRequest(id);
        toast.success("Approval granted");
      } else {
        await api.rejectRequest(id, "Rejected from admin console");
        toast.message("Request rejected");
      }
      reload();
    } catch (err) {
      toast.error(err.message || "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <Skeleton className="h-48 w-full rounded-xl" />;

  if (error) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-red-600">{error.message}</p>
        </CardBody>
      </Card>
    );
  }

  if (!items.length) {
    return (
      <EmptyState
        title="No pending approvals"
        description="Sensitive agent actions will appear here for staff review."
      />
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <Card key={item.id}>
          <CardBody className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-semibold text-zinc-900">
                  {item.requested_action || "Action"}
                </p>
                <Badge tone="warning">{item.status}</Badge>
              </div>
              <p className="mt-1 text-sm text-zinc-600">
                Order: {item.order_id || "—"} · {formatDate(item.created_at)}
              </p>
              {item.reason ? (
                <p className="mt-2 text-sm text-zinc-700">{item.reason}</p>
              ) : null}
            </div>
            <div className="flex shrink-0 gap-2">
              <Button
                variant="primary"
                disabled={busyId === item.id}
                onClick={() => review(item.id, "approve")}
              >
                <Check className="h-4 w-4" />
                Approve
              </Button>
              <Button
                variant="danger"
                disabled={busyId === item.id}
                onClick={() => review(item.id, "reject")}
              >
                <X className="h-4 w-4" />
                Reject
              </Button>
            </div>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}