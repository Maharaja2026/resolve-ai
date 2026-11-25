import PageHeader from "@/components/shared/PageHeader";
import TicketsTable from "@/components/orders/TicketsTable";

export default function CustomerTicketsPage() {
  return (
    <>
      <PageHeader
        title="Support tickets"
        description="Tickets created by the agent or escalations appear here."
      />
      <TicketsTable />
    </>
  );
}