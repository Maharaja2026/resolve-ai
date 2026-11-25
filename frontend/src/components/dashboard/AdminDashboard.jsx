"use client";

import {
  BarChart3,
  Bot,
  ClipboardCheck,
  Ticket,
} from "lucide-react";
import { api } from "@/services/api";
import { useApiQuery } from "@/hooks/useApiQuery";
import StatGrid from "@/components/dashboard/StatGrid";
import { Card, CardBody, CardHeader } from "@/components/shared/Card";

export default function AdminDashboard() {
  const overviewQuery = useApiQuery(() => api.getAnalyticsOverview());
  const approvalStatsQuery = useApiQuery(() => api.getApprovalStats());

  const loading = overviewQuery.loading || approvalStatsQuery.loading;
  const overview = overviewQuery.data;
  const approvalStats = approvalStatsQuery.data;

  const stats = [
    {
      label: "Open tickets",
      value: overview?.open_tickets ?? "—",
      icon: Ticket,
    },
    {
      label: "Pending approvals",
      value: overview?.waiting_approvals ?? "—",
      icon: ClipboardCheck,
    },
    {
      label: "Agent runs",
      value: overview?.total_agent_runs ?? "—",
      icon: Bot,
      hint: `${overview?.completed_runs ?? 0} completed`,
    },
    {
      label: "Resolved tickets",
      value: overview?.resolved_tickets ?? "—",
      icon: BarChart3,
    },
  ];

  return (
    <Standard className="space-y-6">
      <StatGrid stats={stats} loading={loading} />
      <Standard className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-zinc-900">Queue health</h2>
          </CardHeader>
          <CardBody className="space-y-2 text-sm text-zinc-700">
            {overviewQuery.error ? (
              <p className="text-red-600">{overviewQuery.error.message}</p>
            ) : (
              <>
                <Row label="Total tickets" value={overview?.total_tickets} />
                <Row label="Open / in progress" value={overview?.open_tickets} />
                <Row label="Resolved" value={overview?.resolved_tickets} />
              </>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-zinc-900">Approval pipeline</h2>
          </CardHeader>
          <CardBody className="space-y-2 text-sm text-zinc-700">
            {approvalStatsQuery.error ? (
              <p className="text-red-600">{approvalStatsQuery.error.message}</p>
            ) : (
              <>
                <Row label="Pending" value={approvalStats?.pending} />
                <Row label="Approved" value={approvalStats?.approved} />
                <Row label="Rejected" value={approvalStats?.rejected} />
                <Row label="Expired" value={approvalStats?.expired} />
              </>
            )}
          </CardBody>
        </Card>
      </Standard>
    </Standard>
  );
}

function Row({ label, value }) {
  return (
    <Standard className="flex items-center justify-between border-b border-zinc-100 py-2 last:border-0">
      <span>{label}</span>
      <span className="font-semibold text-zinc-900">{value ?? "—"}</span>
    </Standard>
  );
}

function Standard({ children, className }) {
  return <div className={className}>{children}</div>;
}