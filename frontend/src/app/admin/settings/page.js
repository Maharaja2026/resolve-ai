"use client";

import PageHeader from "@/components/shared/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/shared/Card";
import Skeleton from "@/components/shared/Skeleton";
import { useApiQuery } from "@/hooks/useApiQuery";
import { api } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";

export default function AdminSettingsPage() {
  const { profile } = useAuth();
  const healthQuery = useApiQuery(() => api.getHealth());
  const llmQuery = useApiQuery(() => api.getLlmStatus());
  const permissionsQuery = useApiQuery(() => api.getPermissions());

  return (
    <>
      <PageHeader
        title="Settings"
        description="Environment health, LLM providers, and your staff permissions."
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-zinc-900">Profile</h2>
          </CardHeader>
          <CardBody className="space-y-2 text-sm text-zinc-700">
            <Row label="Email" value={profile?.email} />
            <Row label="Role" value={profile?.role} />
            <Row label="Name" value={profile?.profile?.full_name} />
          </CardBody>
        </Card>
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-zinc-900">API health</h2>
          </CardHeader>
          <CardBody className="text-sm text-zinc-700">
            {healthQuery.loading ? (
              <Skeleton className="h-16 w-full" />
            ) : healthQuery.error ? (
              <p className="text-red-600">{healthQuery.error.message}</p>
            ) : (
              <ul className="space-y-2">
                <Row label="Status" value={healthQuery.data?.status} />
                <Row label="Environment" value={healthQuery.data?.environment} />
                <Row
                  label="Supabase"
                  value={
                    healthQuery.data?.supabase_configured ? "configured" : "missing"
                  }
                />
              </ul>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-zinc-900">LLM providers</h2>
          </CardHeader>
          <CardBody className="text-sm text-zinc-700">
            {llmQuery.loading ? (
              <Skeleton className="h-16 w-full" />
            ) : llmQuery.error ? (
              <p className="text-red-600">{llmQuery.error.message}</p>
            ) : (
              <ul className="space-y-2">
                <Row label="Primary" value={llmQuery.data?.primary_provider} />
                <Row label="Fallback" value={llmQuery.data?.fallback_provider} />
                <Row label="Embedding" value={llmQuery.data?.embedding?.model} />
              </ul>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-zinc-900">Permissions</h2>
          </CardHeader>
          <CardBody className="text-sm text-zinc-700">
            {permissionsQuery.loading ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              <ul className="space-y-2">
                <Row label="Can approve" value={String(permissionsQuery.data?.can_approve)} />
                <Row label="Admin" value={String(permissionsQuery.data?.can_admin)} />
                <Row
                  label="View all tickets"
                  value={String(permissionsQuery.data?.can_view_all_tickets)}
                />
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </>
  );
}

function Row({ label, value }) {
  return (
    <li className="flex items-center justify-between border-b border-zinc-100 py-2 last:border-0">
      <span>{label}</span>
      <span className="font-medium capitalize text-zinc-900">{value ?? "—"}</span>
    </li>
  );
}