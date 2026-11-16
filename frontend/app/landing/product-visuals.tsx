/**
 * Ảnh minh hoạ giao diện dựng bằng markup cho từng khả năng của trang Product
 * (mẫu Intercom "product features": mỗi khả năng đi cùng màn tương ứng). Dữ
 * liệu trong ảnh là ví dụ minh hoạ, không phải phản hồi thật.
 */

function Window({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <figure aria-hidden className="hn-frame overflow-hidden p-0 select-none">
      <div className="flex items-center gap-2 border-b border-[var(--hn-olive)] px-4 py-2.5">
        <span className="size-2 bg-[var(--hn-olive)]" />
        <span className="size-2 bg-[var(--hn-olive)]" />
        <span className="size-2 bg-[var(--hn-olive)]" />
        <span className="hn-pixel ml-2 text-[9px] tracking-widest text-[var(--hn-stone)] uppercase">{title}</span>
      </div>
      <div className="relative z-[1] p-5">{children}</div>
    </figure>
  )
}

function ListenVisual() {
  const rows = [
    ["review_text", "“App trả lời sai giờ mở cửa…”", "Nội dung phản hồi"],
    ["created", "2026-10-02 08:14", "Ngày phản hồi"],
    ["channel", "app_store", "Thông tin nguồn"],
    ["user_email", "[EMAIL]", "Bỏ qua"],
  ] as const
  return (
    <Window title="Map columns · Gate 1">
      <ul className="flex flex-col gap-2 text-xs">
        {rows.map(([col, sample, target]) => (
          <li key={col} className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,0.9fr)] items-center gap-3 border border-[var(--hn-olive)]/70 bg-[var(--hn-deep)] px-3 py-2">
            <span className="min-w-0">
              <span className="block font-mono text-[var(--hn-ivory)]">{col}</span>
              <span className="block truncate text-[var(--hn-stone)]">{sample}</span>
            </span>
            <span className="text-[var(--hn-gold)]">→</span>
            <span className={target === "Bỏ qua" ? "text-[var(--hn-stone)] line-through" : "text-[var(--hn-soft)]"}>{target}</span>
          </li>
        ))}
      </ul>
    </Window>
  )
}

function UnderstandVisual() {
  return (
    <Window title="Finding · Gate 2">
      <p className="hn-display text-lg leading-snug">Giờ mở cửa sai chiếm 38% phàn nàn tuần này</p>
      <div className="mt-3 flex items-center gap-3 text-[11px] text-[var(--hn-stone)]">
        <span>Độ tin cậy</span>
        <span className="h-1.5 flex-1 bg-[var(--hn-moss)]">
          <span className="block h-full w-[78%] bg-[var(--hn-soft)]" />
        </span>
        <span className="font-mono">78%</span>
      </div>
      <div className="mt-4 flex flex-wrap gap-1.5 text-[11px]">
        {["1 Phân bố chủ đề", "2 Xu hướng 7 ngày", "3 Trích dẫn"].map((chip) => (
          <span key={chip} className="border border-[var(--hn-olive)] px-2 py-0.5 text-[var(--hn-soft)]">{chip}</span>
        ))}
      </div>
      <div className="mt-5 flex gap-2 text-[11px]">
        <span className="bg-[var(--hn-gold)] px-2.5 py-1 font-semibold text-[var(--hn-deep)]">Duyệt</span>
        <span className="border border-[var(--hn-olive)] px-2.5 py-1">Sửa</span>
        <span className="border border-[var(--hn-olive)] px-2.5 py-1">Điều tra thêm</span>
      </div>
    </Window>
  )
}

function ActVisual() {
  const dots = [
    { left: "22%", bottom: "74%", c: "var(--hn-gold)" },
    { left: "34%", bottom: "62%", c: "var(--hn-soft)" },
    { left: "70%", bottom: "80%", c: "var(--hn-soft)" },
    { left: "28%", bottom: "24%", c: "var(--hn-stone)" },
    { left: "78%", bottom: "30%", c: "var(--hn-stone)" },
  ]
  return (
    <Window title="Priority matrix · Gate 3">
      <div className="relative aspect-[4/3] border border-[var(--hn-olive)] bg-[var(--hn-deep)]">
        <span className="absolute top-0 left-1/2 h-full w-px bg-[var(--hn-olive)]" />
        <span className="absolute top-1/2 left-0 h-px w-full bg-[var(--hn-olive)]" />
        {/* Font pixel không có dấu tiếng Việt — nhãn tiếng Việt dùng font chữ thường. */}
        <span className="absolute top-2 left-2 text-[10px] font-semibold tracking-wide text-[var(--hn-soft)] uppercase">Làm ngay</span>
        <span className="absolute top-2 right-2 text-[10px] font-semibold tracking-wide text-[var(--hn-stone)] uppercase">Chiến lược</span>
        {dots.map((d, i) => (
          <span
            key={i}
            className="absolute size-3 -translate-x-1/2 translate-y-1/2 rounded-full ring-2 ring-[var(--hn-deep)]"
            style={{ left: d.left, bottom: d.bottom, background: d.c }}
          />
        ))}
      </div>
      <p className="mt-3 text-[11px] text-[var(--hn-stone)]">Kỹ thuật · Thêm giờ mở cửa theo chi nhánh — chờ bạn nhận</p>
    </Window>
  )
}

export const PRODUCT_VISUALS: Record<string, () => React.ReactNode> = {
  listen: ListenVisual,
  understand: UnderstandVisual,
  act: ActVisual,
}
