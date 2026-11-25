import PageHeader from "@/components/shared/PageHeader";
import OrdersTable from "@/components/orders/OrdersTable";

export default function CustomerOrdersPage() {
  return (
    <>
      <PageHeader
        title="Orders"
        description="Live data from GET /api/v1/orders scoped to your customer profile."
      />
      <OrdersTable />
    </>
  );
}