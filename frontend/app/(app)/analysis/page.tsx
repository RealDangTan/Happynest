import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";

export default function AnalysisPage() {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyTitle>Analysis runs</EmptyTitle>
        <EmptyDescription>Sắp có sau FE-04 (trigger run, tiến độ, kết quả).</EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}
