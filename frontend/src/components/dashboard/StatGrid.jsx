import { Card, CardBody } from "@/components/shared/Card";
import Skeleton from "@/components/shared/Skeleton";

export default function StatGrid({ stats, loading }) {
  if (loading) {
    return (
      <Standard className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </Standard>
    );
  }

  return (
    <Standard className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <Card key={stat.label}>
            <CardBody className="flex items-start justify-between gap-3">
              <Standard>
                <p className="text-sm font-medium text-zinc-600">{stat.label}</p>
                <p className="mt-1 text-2xl font-semibold tracking-tight text-zinc-900">
                  {stat.value}
                </p>
                {stat.hint ? (
                  <p className="mt-1 text-xs text-zinc-500">{stat.hint}</p>
                ) : null}
              </Standard>
              {Icon ? (
                <Standard className="rounded-lg bg-teal-50 p-2 text-teal-700">
                  <Icon className="h-5 w-5" aria-hidden />
                </Standard>
              ) : null}
            </CardBody>
          </Card>
        );
      })}
    </Standard>
  );
}

function Standard({ children, className }) {
  return <div className={className}>{children}</div>;
}