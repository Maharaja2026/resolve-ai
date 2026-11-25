import PageHeader from "@/components/shared/PageHeader";
import ApprovalsPanel from "@/components/approvals/ApprovalsPanel";

export default function AdminApprovalsPage() {
  return (
    <>
      <PageHeader
        title="Approval queue"
        description="Review pending agent actions via the approvals API."
      />
      <ApprovalsPanel />
    </>
  );
}