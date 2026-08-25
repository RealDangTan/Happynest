import { describe, expect, it } from "vitest";
import { guessAll, guessColumn } from "./csv-mapping";

describe("guessColumn", () => {
  it("khớp tên chuẩn trực tiếp", () => {
    expect(guessColumn("source", ["source", "content"])).toBe("source");
    expect(guessColumn("content", ["id", "content", "note"])).toBe("content");
  });

  it("khớp alias tiếng Việt có dấu và khoảng trắng thừa", () => {
    expect(guessColumn("source", ["  Nguồn ", "Nội dung"])).toBe("  Nguồn ");
    expect(guessColumn("content", ["stt", "Nội dung"])).toBe("Nội dung");
    expect(guessColumn("created_at", ["Ngày", "ghi chú"])).toBe("Ngày");
  });

  it("trả rỗng khi không đoán được", () => {
    expect(guessColumn("external_ref", ["a", "b"])).toBe("");
  });
});

describe("guessAll", () => {
  it("đoán đủ 4 trường từ header kiểu khảo sát", () => {
    const g = guessAll(["Thời điểm", "Kênh", "Ý kiến", "Mã"]);
    expect(g.source).toBe("Kênh");
    expect(g.content).toBe("Ý kiến");
    expect(g.created_at).toBe("Thời điểm");
    expect(g.external_ref).toBe(""); // "Mã" không nằm trong alias
  });
});
