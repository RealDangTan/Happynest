// FE-03b T4: chuẩn hoá raw CSV phía client — hàm thuần để test được.
export type TargetField = "source" | "content" | "external_ref" | "created_at";

export const TARGETS: {
  key: TargetField;
  label: string;
  required: boolean;
}[] = [
  { key: "source", label: "Nguồn", required: true },
  { key: "content", label: "Nội dung", required: true },
  { key: "external_ref", label: "Tham chiếu ngoài", required: false },
  { key: "created_at", label: "Ngày tạo", required: false },
];

// Auto-guess: khớp tên thường trực + alias vi/en phổ biến.
const ALIASES: Record<TargetField, string[]> = {
  source: ["source", "nguồn", "nguon", "platform", "channel", "kênh"],
  content: [
    "content",
    "nội dung",
    "noi dung",
    "text",
    "review",
    "comment",
    "body",
    "feedback",
    "ý kiến",
    "y kien",
    "phản hồi",
    "phan hoi",
  ],
  external_ref: [
    "external_ref",
    "externalref",
    "ref",
    "reference",
    "id",
    "url",
    "link",
  ],
  created_at: [
    "created_at",
    "createdat",
    "created",
    "date",
    "time",
    "timestamp",
    "ngày",
    "ngay",
    "thời điểm",
    "thoi diem",
  ],
};

/** Đoán cột file khớp với trường mục tiêu; "" nếu không đoán được. */
export function guessColumn(field: TargetField, fields: string[]): string {
  const normalized = fields.map((f) => f.trim().toLowerCase());
  const hit = ALIASES[field].find((a) => normalized.includes(a));
  if (!hit) return "";
  return fields[normalized.indexOf(hit)] ?? "";
}

/** Map toàn bộ 4 trường mục tiêu một lượt (dùng khi mở bước map). */
export function guessAll(
  fields: string[],
): Partial<Record<TargetField, string>> {
  return Object.fromEntries(
    TARGETS.map(({ key }) => [key, guessColumn(key, fields)]),
  );
}

export const CANON_HEADERS = ["source", "content", "external_ref", "created_at"];
