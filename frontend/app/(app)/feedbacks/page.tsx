import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";

export default function FeedbacksPage() {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyTitle>Phản hồi</EmptyTitle>
        <EmptyDescription>Sắp có sau FE-03 (list, filter, import CSV).</EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}
