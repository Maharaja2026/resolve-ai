"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/services/api";
import { useApiQuery } from "@/hooks/useApiQuery";
import { Card, CardBody, CardHeader } from "@/components/shared/Card";
import Skeleton from "@/components/shared/Skeleton";

export default function AnalyticsCharts() {
  const perfQuery = useApiQuery(() => api.getAgentPerformance());
  const toolQuery = useApiQuery(() => api.getToolUsage());

  const providerData = Object.entries(perfQuery.data?.by_provider || {}).map(
    ([name, stats]) => ({
      name,
      runs: stats.runs,
      toolCalls: stats.tool_calls,
    }),
  );

  const toolData = Object.entries(toolQuery.data?.tools || {}).map(
    ([name, stats]) => ({
      name,
      count: stats.count,
      failed: stats.failed,
    }),
  );

  if (perfQuery.loading || toolQuery.loading) {
    return <Skeleton className="h-72 w-full rounded-xl" />;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <h3 className="font-semibold text-zinc-900">Runs by provider</h3>
        </CardHeader>
        <CardBody className="h-72">
          {providerData.length === 0 ? (
            <p className="text-sm text-zinc-500">No agent runs recorded yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={providerData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="runs" fill="#0d9488" name="Runs" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardBody>
      </Card>
      <Card>
        <CardHeader>
          <h3 className="font-semibold text-zinc-900">Tool usage</h3>
        </CardHeader>
        <CardBody className="h-72">
          {toolData.length === 0 ? (
            <p className="text-sm text-zinc-500">No tool executions yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={toolData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={60} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#334155" name="Calls" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardBody>
      </Card>
    </div>
  );
}