import PageHeader from "@/components/shared/PageHeader";
import AnalyticsCharts from "@/components/agent/AnalyticsCharts";

export default function AdminAnalyticsPage() {
  return (
    <>
      <PageHeader
        title="Analytics"
        description="Agent performance and tool usage from the analytics API."
      />
      <AnalyticsCharts />
    </>
  );
}