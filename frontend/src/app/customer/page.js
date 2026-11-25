import PageHeader from "@/components/shared/PageHeader";
import CustomerDashboard from "@/components/dashboard/CustomerDashboard";

export default function CustomerHomePage() {
  return (
    <>
      <PageHeader
        title="Customer dashboard"
        description="Track orders, tickets, and AI support conversations backed by the ResolveAI API."
      />
      <CustomerDashboard />
    </>
  );
}