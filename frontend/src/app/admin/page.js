import PageHeader from "@/components/shared/PageHeader";
import AdminDashboard from "@/components/dashboard/AdminDashboard";

export default function AdminHomePage() {
  return (
    <>
      <PageHeader
        title="Operations dashboard"
        description="Queue metrics from /api/v1/analytics for staff and administrators."
      />
      <AdminDashboard />
    </>
  );
}