import PageHeader from "@/components/shared/PageHeader";
import AgentRunLookup from "@/components/agent/AgentRunLookup";

export default function AdminAgentRunsPage() {
  return (
    <>
      <PageHeader
        title="Agent runs"
        description="Inspect traces for individual runs (staff-only trace endpoint)."
      />
      <AgentRunLookup />
    </>
  );
}