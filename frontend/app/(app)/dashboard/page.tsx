import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";

export default function DashboardPage() {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyTitle>Tổng quan</EmptyTitle>
        <EmptyDescription>Sắp có sau pha P4 — dashboard PM với chart thật.</EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}
