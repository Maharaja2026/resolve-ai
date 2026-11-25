import PageHeader from "@/components/shared/PageHeader";
import TicketsTable from "@/components/orders/TicketsTable";

export default function AdminTicketsPage() {
  return (
    <>
      <PageHeader
        title="All tickets"
        description="Staff view of resolveai_support_tickets."
      />
      <TicketsTable staff />
    </>
  );
}