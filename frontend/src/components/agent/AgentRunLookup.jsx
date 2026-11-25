"use client";

import { useEffect, useState } from "react";
import { Search, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/services/api";
import Button from "@/components/shared/Button";
import Input from "@/components/shared/Input";
import { Card, CardBody, CardHeader } from "@/components/shared/Card";
import Badge from "@/components/shared/Badge";
import EmptyState from "@/components/shared/EmptyState";
import Skeleton from "@/components/shared/Skeleton";
import { formatDate } from "@/lib/utils";

export default function AgentRunLookup() {
  const [runId, setRunId] = useState("");
  const [trace, setTrace] = useState(null);
  const [loading, setLoading] = useState(false);
  const [runs, setRuns] = useState([]);
  const [listLoading, setListLoading] = useState(true);

  const loadRuns = async () => {
    setListLoading(true);
    try {
      const data = await api.listAgentRuns({ limit: 40 });
      setRuns(data.items || []);
    } catch (err) {
      toast.error(err.message || "Could not load agent runs");
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const loadTrace = async (id) => {
    if (!id?.trim()) return;
    setLoading(true);
    try {
      const data = await api.getAgentRunTrace(id.trim());
      setTrace(data);
      setRunId(id.trim());
    } catch (err) {
      setTrace(null);
      toast.error(err.message || "Run not found");
    } finally {
      setLoading(false);
    }
  };

  const handleLookup = async (e) => {
    e.preventDefault();
    await loadTrace(runId);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex items-center justify-between gap-3">
          <h2 className="font-semibold text-zinc-900">Recent agent runs</h2>
          <Button type="button" variant="secondary" onClick={loadRuns} disabled={listLoading}>
            <RefreshCw className={`h-4 w-4 ${listLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </CardHeader>
        <CardBody>
          {listLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : runs.length === 0 ? (
            <EmptyState
              title="No agent runs yet"
              description="Runs appear here after customers send support chat messages."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-zinc-200 text-xs uppercase text-zinc-500">
                  <tr>
                    <th className="px-2 py-2 font-medium">Started</th>
                    <th className="px-2 py-2 font-medium">Intent</th>
                    <th className="px-2 py-2 font-medium">Status</th>
                    <th className="px-2 py-2 font-medium">Provider</th>
                    <th className="px-2 py-2 font-medium">Steps</th>
                    <th className="px-2 py-2 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id} className="border-b border-zinc-100">
                      <td className="px-2 py-2 text-zinc-600">{formatDate(run.started_at)}</td>
                      <td className="px-2 py-2 text-zinc-800">{run.intent || "—"}</td>
                      <td className="px-2 py-2">
                        <Badge tone="info">{run.status}</Badge>
                      </td>
                      <td className="px-2 py-2 text-zinc-600">
                        {run.selected_provider || "—"}
                      </td>
                      <td className="px-2 py-2 text-zinc-600">
                        {run.total_steps ?? 0}/{run.total_tool_calls ?? 0}
                      </td>
                      <td className="px-2 py-2 text-right">
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => loadTrace(run.id)}
                          disabled={loading}
                        >
                          Trace
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-semibold text-zinc-900">Inspect agent run</h2>
        </CardHeader>
        <CardBody>
          <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleLookup}>
            <Input
              value={runId}
              onChange={(e) => setRunId(e.target.value)}
              placeholder="Paste agent run UUID"
            />
            <Button type="submit" disabled={loading}>
              <Search className="h-4 w-4" />
              Load trace
            </Button>
          </form>
        </CardBody>
      </Card>

      {trace ? (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold text-zinc-900">Run {trace.run?.id}</h3>
              <Badge tone="info">{trace.run?.status}</Badge>
            </div>
          </CardHeader>
          <CardBody className="space-y-4 text-sm">
            <p className="text-zinc-600">
              Provider: {trace.run?.selected_provider || "—"} · Model:{" "}
              {trace.run?.selected_model || "—"} · Steps: {trace.run?.total_steps ?? 0} ·
              Tools: {trace.run?.total_tool_calls ?? 0}
            </p>
            {trace.run?.input_message ? (
              <p className="rounded-lg bg-zinc-50 px-3 py-2 text-zinc-700">
                {trace.run.input_message}
              </p>
            ) : null}
            <div>
              <p className="mb-2 font-medium text-zinc-900">Events</p>
              <ul className="space-y-2">
                {(trace.events || []).map((event) => (
                  <li
                    key={event.id}
                    className="rounded-lg border border-zinc-100 px-3 py-2"
                  >
                    <p className="font-medium text-zinc-800">
                      #{event.sequence_number} {event.event_name}
                    </p>
                    <p className="text-xs text-zinc-500">{event.summary}</p>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mb-2 font-medium text-zinc-900">Tool executions</p>
              <ul className="space-y-2">
                {(trace.tool_executions || []).map((tool) => (
                  <li
                    key={tool.id}
                    className="rounded-lg border border-zinc-100 px-3 py-2"
                  >
                    <p className="font-medium text-zinc-800">{tool.tool_name}</p>
                    <p className="text-xs text-zinc-500">
                      {tool.status} · {formatDate(tool.started_at)}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          </CardBody>
        </Card>
      ) : null}
    </div>
  );
}
