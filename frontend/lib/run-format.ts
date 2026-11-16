import type { RunProgress } from "./types";

/** Thời lượng lượt chạy dạng "1 phút 05 giây"; lượt đang chạy tính tới `now`. */
export function runDuration(run: Pick<RunProgress, "started_at" | "completed_at">, now = Date.now()): string {
  const start = Date.parse(run.started_at);
  const end = run.completed_at ? Date.parse(run.completed_at) : now;
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return "—";
  const total = Math.round((end - start) / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h} giờ ${String(m).padStart(2, "0")} phút`;
  if (m > 0) return `${m} phút ${String(s).padStart(2, "0")} giây`;
  return `${s} giây`;
}

/** Nhãn ngắn của phạm vi lượt phân loại. */
export function runScopeLabel(run: Pick<RunProgress, "mode">): string {
  return run.mode === "batch" ? "Cả lô nhập" : run.mode === "selected" ? "Mục đã chọn" : "Phân loại";
}
