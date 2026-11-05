"""Generate simplified Chapter 3 diagrams as HTML+SVG, rendered to PNG by headless Chrome.

Usage: python -I make_figs.py <outdir>
"""
import html
import os
import subprocess
import sys

FONT = "'Times New Roman', Times, serif"
FS = 23          # box text size (CSS px)
LH = 1.22        # line height factor
INK = "#1f2933"
STYLES = {
    # kind: (fill, stroke, stroke-width, dash)
    "human": ("#d6e4f2", "#1f2933", 3.2, None),
    "ai": ("#e9e9e9", "#1f2933", 1.6, None),
    "prog": ("#ffffff", "#1f2933", 1.6, None),
    "ext": ("#ffffff", "#1f2933", 1.6, "7,5"),
    "band": ("#f3f5f8", "#a7b1bc", 1.2, None),
    "plain": ("none", "none", 0, None),
}


class Fig:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts = []
        self.nodes = {}

    # ---------- primitives ----------
    def rect(self, x, y, w, h, kind="prog", rx=10):
        fill, stroke, sw, dash = STYLES[kind]
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>'
        )

    def text(self, x, y, s, size=FS, anchor="middle", weight="normal", style="normal",
             color=INK, halo=False, rotate=None):
        extra = ""
        if halo:
            extra = ' paint-order="stroke" stroke="#ffffff" stroke-width="7" stroke-linejoin="round"'
        rot = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" '
            f'font-style="{style}" fill="{color}" dominant-baseline="middle"{extra}{rot}>'
            f"{html.escape(s)}</text>"
        )

    def lines(self, cx, cy, lines, size=FS, bold_first=False, anchor="middle", x_left=None):
        n = len(lines)
        step = size * LH
        y0 = cy - step * (n - 1) / 2
        for i, s in enumerate(lines):
            w = "bold" if (bold_first and i == 0) else "normal"
            if anchor == "start":
                self.text(x_left, y0 + i * step, s, size=size, anchor="start", weight=w)
            else:
                self.text(cx, y0 + i * step, s, size=size, weight=w)

    def box(self, name, x, y, w, h, lines, kind="prog", bold_first=False, size=FS):
        self.rect(x, y, w, h, kind)
        self.lines(x + w / 2, y + h / 2, lines, size=size, bold_first=bold_first)
        self.nodes[name] = (x, y, w, h)

    def ellipse(self, name, cx, cy, rx, ry, lines, kind="prog", size=FS - 2):
        fill, stroke, sw, _ = STYLES[kind]
        self.parts.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
        )
        self.lines(cx, cy, lines, size=size)
        self.nodes[name] = (cx - rx, cy - ry, 2 * rx, 2 * ry)

    def arrow(self, pts, dashed=False, head=True, width=1.8):
        d = " ".join(f"{x},{y}" for x, y in pts)
        dash = ' stroke-dasharray="8,6"' if dashed else ""
        mk = ' marker-end="url(#ah)"' if head else ""
        self.parts.append(
            f'<polyline points="{d}" fill="none" stroke="{INK}" stroke-width="{width}"{dash}{mk}/>'
        )

    def line(self, pts, dashed=False, width=1.6):
        self.arrow(pts, dashed=dashed, head=False, width=width)

    # anchor helpers
    def c(self, n):
        x, y, w, h = self.nodes[n]
        return x + w / 2, y + h / 2

    def top(self, n, dx=0):
        x, y, w, h = self.nodes[n]
        return x + w / 2 + dx, y

    def bot(self, n, dx=0):
        x, y, w, h = self.nodes[n]
        return x + w / 2 + dx, y + h

    def left(self, n, dy=0):
        x, y, w, h = self.nodes[n]
        return x, y + h / 2 + dy

    def right(self, n, dy=0):
        x, y, w, h = self.nodes[n]
        return x + w, y + h / 2 + dy

    def legend(self, y, items=("human", "ai", "prog"), x0=None):
        labels = {
            "human": "Người phụ trách quyết định",
            "ai": "Có gọi dịch vụ AI",
            "prog": "Chương trình xử lý",
            "ext": "Ngoài hệ thống / chưa có màn hình",
        }
        widths = {"human": 300, "ai": 230, "prog": 250, "ext": 380}
        total = sum(widths[k] for k in items)
        x = x0 if x0 is not None else (self.w - total) / 2
        for k in items:
            self.rect(x, y - 13, 40, 26, k, rx=5)
            self.text(x + 50, y + 1, labels[k], size=FS - 3, anchor="start")
            x += widths[k]

    def svg(self):
        defs = (
            '<defs><marker id="ah" viewBox="0 0 10 10" refX="9.2" refY="5" markerWidth="9" '
            'markerHeight="9" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
            f'fill="{INK}"/></marker></defs>'
        )
        body = "\n".join(self.parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" font-family="{FONT}">{defs}'
            f'<rect width="100%" height="100%" fill="#ffffff"/>{body}</svg>'
        )


# ------------------------------------------------------------------ figures

def fig_process():
    """Hình 3.1 — Quy trình nghiệp vụ (một cột, ba điểm kiểm duyệt)."""
    f = Fig(900, 1000)
    X, W, H, G = 220, 460, 78, 34
    rows = [
        ("src", ["Phản hồi từ nhiều nguồn", "(tệp CSV)"], "prog", False),
        ("g1", ["Điểm kiểm duyệt 1", "xác nhận ý nghĩa các cột"], "human", True),
        ("lis", ["LẮNG NGHE", "che thông tin, gắn chủ đề, phân cụm"], "ai", True),
        ("und", ["THẤU HIỂU", "tác tử tra cứu, tạo nhận định"], "ai", True),
        ("g2", ["Điểm kiểm duyệt 2", "duyệt nhận định"], "human", True),
        ("act", ["HÀNH ĐỘNG", "đề xuất phương án, tính điểm ưu tiên"], "ai", True),
        ("g3", ["Điểm kiểm duyệt 3", "chọn, sửa hoặc từ chối phương án"], "human", True),
        ("out", ["Triển khai cải tiến", "(ngoài hệ thống)"], "ext", False),
    ]
    y = 20
    for name, ls, kind, bold in rows:
        f.box(name, X, y, W, H, ls, kind, bold_first=bold)
        y += H + G
    order = [r[0] for r in rows]
    for a, b in zip(order, order[1:]):
        f.arrow([f.bot(a), f.top(b)])
    # side inputs
    f.box("tax", 715, f.nodes["lis"][1] + 6, 170, 66, ["Áp dụng", "bộ chủ đề"], "human", size=FS - 2)
    f.arrow([f.left("tax"), f.right("lis")])
    f.box("q", 15, f.nodes["und"][1] + 6, 170, 66, ["Đặt câu hỏi", "điều tra"], "prog", size=FS - 2)
    f.arrow([f.right("q"), f.left("und")])
    # loop investigate more
    gx, gy = f.right("g2")
    ux, uy = f.right("und")
    f.arrow([(gx, gy), (gx + 70, gy), (gx + 70, uy + 18), (ux, uy + 18)], dashed=True)
    f.text(gx + 82, (gy + uy) / 2 + 8, "yêu cầu", size=FS - 3, anchor="start", style="italic")
    f.text(gx + 82, (gy + uy) / 2 + 36, "điều tra thêm", size=FS - 3, anchor="start", style="italic")
    f.h = y + 30
    f.legend(y + 2, items=("human", "ai", "prog"))
    f.h = y + 30
    return f


def fig_usecase():
    """Hình 3.2 — Use case rút gọn."""
    f = Fig(1000, 760)
    bx, bw = 150, 690
    f.rect(bx, 10, bw, 730, "prog", rx=4)
    f.text(bx + bw / 2, 38, "Hệ thống HappyNest", size=FS + 1, weight="bold")
    groups = [
        ("Tài khoản và sản phẩm", [(["Đăng nhập"], "prog"), (["Quản lý", "sản phẩm"], "prog")]),
        ("Lắng nghe", [(["Nhập CSV, xác nhận", "cột (kiểm duyệt 1)"], "human"),
                       (["Quản lý", "bộ chủ đề"], "prog"),
                       (["Phân loại,", "phân cụm phản hồi"], "prog")]),
        ("Thấu hiểu", [(["Đặt câu hỏi", "điều tra"], "prog"),
                       (["Duyệt nhận định", "(kiểm duyệt 2)"], "human"),
                       (["Xem báo cáo", "nhận định"], "prog")]),
        ("Hành động", [(["Sinh phương án", "cải tiến"], "prog"),
                       (["Chọn, sửa phương án", "(kiểm duyệt 3)"], "human"),
                       (["Xem phương án theo", "nhóm nghiệp vụ"], "prog")]),
    ]
    gy, gh, gap = 62, 150, 18
    band_mid = []
    for gi, (title, ucs) in enumerate(groups):
        y = gy + gi * (gh + gap)
        f.rect(bx + 15, y, bw - 30, gh, "band", rx=4)
        f.text(bx + 30, y + 22, title, size=FS - 1, anchor="start", weight="bold")
        n = len(ucs)
        slot = (bw - 30) / 3
        startx = bx + 15 + (3 - n) * slot / 2
        for i, (ls, kind) in enumerate(ucs):
            cx = startx + slot * i + slot / 2
            f.ellipse(f"u{gi}{i}", cx, y + 90, 107, 45, ls, kind, size=FS - 3)
        band_mid.append(y + gh / 2)
    # actors
    def actor(cx, cy, label):
        f.parts.append(f'<circle cx="{cx}" cy="{cy - 52}" r="17" fill="#fff" stroke="{INK}" stroke-width="2.4"/>')
        f.line([(cx, cy - 35), (cx, cy + 12)], width=2.4)
        f.line([(cx - 26, cy - 18), (cx + 26, cy - 18)], width=2.4)
        f.line([(cx, cy + 12), (cx - 20, cy + 45)], width=2.4)
        f.line([(cx, cy + 12), (cx + 20, cy + 45)], width=2.4)
        for i, s in enumerate(label):
            f.text(cx, cy + 70 + i * 27, s, size=FS - 2)
    hx, hy = 70, 380
    actor(hx, hy, ["Người", "phụ trách"])
    for m in band_mid:
        f.line([(hx + 28, hy - 18), (bx + 15, m)])
    ax, ay = 925, 420
    actor(ax, ay, ["Dịch vụ AI"])
    for m in band_mid[1:]:
        f.line([(ax - 28, ay - 18), (bx + bw - 15, m)], dashed=True)
    return f


def fig_arch():
    """Hình 3.3 — Kiến trúc ba tầng."""
    f = Fig(1000, 720)
    # bands
    f.rect(10, 10, 980, 130, "band", rx=4)
    f.text(28, 75, "Giao diện", size=FS - 1, weight="bold", rotate=-90)
    f.rect(10, 155, 980, 370, "band", rx=4)
    f.text(28, 340, "Xử lý", size=FS - 1, weight="bold", rotate=-90)
    f.rect(10, 540, 980, 170, "band", rx=4)
    f.text(28, 625, "Dữ liệu", size=FS - 1, weight="bold", rotate=-90)
    f.box("br", 70, 38, 230, 76, ["Trình duyệt của", "người phụ trách"], "prog")
    f.box("fe", 370, 30, 420, 92, ["Giao diện web (Next.js)", "màn hình theo ba bước"], "prog", bold_first=True)
    f.arrow([f.right("br"), f.left("fe")])
    # server
    f.rect(70, 180, 640, 325, "prog", rx=10)
    f.text(390, 210, "Máy chủ ứng dụng (FastAPI)", size=FS, weight="bold")
    f.box("l", 95, 240, 185, 120, ["Lắng nghe", "nhập, phân loại,", "phân cụm"], "prog", bold_first=True, size=FS - 2)
    f.box("u", 298, 240, 185, 120, ["Thấu hiểu", "tác tử điều tra", "(LangGraph)"], "prog", bold_first=True, size=FS - 2)
    f.box("a", 501, 240, 185, 120, ["Hành động", "phương án,", "điểm ưu tiên"], "prog", bold_first=True, size=FS - 2)
    f.box("sh", 95, 385, 591, 96, ["Thành phần dùng chung: che thông tin định danh,",
                                   "gọi mô hình có kiểm tra đầu ra, ghi nhật ký"], "prog", size=FS - 2)
    for n in ("l", "u", "a"):
        f.arrow([f.bot(n), (f.bot(n)[0], 385)])
    fx, fy = f.bot("fe")
    f.arrow([(fx - 30, fy), (fx - 30, 180)])
    f.text(fx - 18, 152, "yêu cầu /api", size=FS - 3, anchor="start", style="italic", halo=True)
    f.box("ai", 760, 290, 205, 120, ["Dịch vụ AI", "bên ngoài"], "ai", bold_first=True)
    sx, sy = f.right("sh")
    f.arrow([(sx, sy), (735, sy), (735, 350), (760, 350)])
    f.text(862, 445, "chỉ nhận văn bản", size=FS - 3, style="italic")
    f.text(862, 472, "đã che thông tin", size=FS - 3, style="italic")
    # data
    f.box("db", 120, 570, 520, 110, ["PostgreSQL + pgvector", "dữ liệu nghiệp vụ, véc-tơ,", "trạng thái lượt điều tra"], "prog", bold_first=True, size=FS - 2)
    f.box("fs", 690, 570, 270, 110, ["Thư mục lưu", "tệp CSV gốc"], "prog")
    f.arrow([(380, 505), (380, 570)])
    f.arrow([(650, 505), (650, 535), (825, 535), (825, 570)])
    return f


def fig_data():
    """Hình 3.4 — Mô hình dữ liệu khái niệm."""
    f = Fig(1000, 700)
    W, H = 200, 78

    def ent(name, x, y, title, sub, kind="prog"):
        f.rect(x, y, W, H, kind, rx=6)
        f.text(x + W / 2, y + 26, title, size=FS - 1, weight="bold")
        f.text(x + W / 2, y + 55, sub, size=FS - 5, style="italic")
        f.nodes[name] = (x, y, W, H)

    ent("acc", 180, 20, "Tài khoản", "người phụ trách")
    ent("prd", 600, 20, "Sản phẩm", "ranh giới dữ liệu")
    f.line([f.right("acc"), f.left("prd")])

    xs = [30, 270, 510, 750]
    ent("imp", xs[0], 190, "Lượt nhập", "tệp CSV, ánh xạ cột")
    ent("fb", xs[1], 190, "Phản hồi", "văn bản đã che, nhãn AI")
    ent("tax", xs[2], 190, "Chủ đề", "bộ chủ đề có phiên bản")
    ent("cl", xs[3], 190, "Cụm", "nhóm phản hồi gần nghĩa")
    # bus from product
    px, py = f.bot("prd")
    busy = 150
    f.line([(px, py), (px, busy)])
    f.line([(xs[0] + W / 2, busy), (xs[3] + W / 2, busy)])
    for n in ("imp", "fb", "tax", "cl"):
        f.line([(f.top(n)[0], busy), f.top(n)])
    f.line([f.right("imp"), f.left("fb")])
    # feedback - cluster relation (curve below)
    fbx, fby = f.bot("fb")
    clx, cly = f.bot("cl")
    f.line([(fbx + 40, fby), (fbx + 40, fby + 22), (clx, fby + 22), (clx, cly)])
    f.text((fbx + clx) / 2 + 60, fby + 22, "thuộc", size=FS - 4, style="italic", halo=True)

    # traceability chain
    cy = 420
    f.rect(50, cy - 40, 940, 150, "band", rx=6)
    f.text(65, cy - 20, "Chuỗi truy vết", size=FS - 3, anchor="start", weight="bold")
    cx = [70, 300, 530, 760]
    ent("run", cx[0], cy, "Lượt điều tra", "câu hỏi, giới hạn")
    ent("ev", cx[1], cy, "Bằng chứng", "kết quả một lần tra cứu")
    ent("ins", cx[2], cy, "Nhận định", "quan sát, giả thuyết")
    ent("act", cx[3], cy, "Phương án", "căn cứ, điểm ưu tiên")
    f.arrow([f.right("run"), f.left("ev")], width=2.2)
    f.arrow([f.right("ev"), f.left("ins")], width=2.2)
    f.arrow([f.right("ins"), f.left("act")], width=2.2)
    # evidence quotes feedback
    ex, ey = f.top("ev")
    f.arrow([(ex, ey), (ex, 330), (f.bot("fb")[0] - 40, 330), (f.bot("fb")[0] - 40, f.bot("fb")[1])], dashed=True)
    f.text(ex + 10, 352, "trích từ", size=FS - 4, anchor="start", style="italic", halo=True)
    # run belongs to product (dashed note via bus) - skip to keep simple
    ent("dec", 400, 600, "Nhật ký quyết định", "giá trị AI và giá trị người", "human")
    dx, dy = f.top("dec")
    f.line([(dx - 60, dy), (dx - 60, 560), (f.bot("ins")[0], 560), f.bot("ins")], dashed=True)
    f.line([(dx + 60, dy), (dx + 60, 575), (f.bot("act")[0], 575), f.bot("act")], dashed=True)
    lx, ly = f.left("imp")
    f.line([(lx, ly), (14, ly), (14, f.left("dec")[1]), f.left("dec")], dashed=True)
    f.text(870, 650, "nét đứt: tham chiếu", size=FS - 5, style="italic")
    f.text(870, 676, "để truy vết", size=FS - 5, style="italic")
    return f


def fig_listen():
    """Hình 3.5 — Luồng bước Lắng nghe."""
    f = Fig(1000, 640)
    W, H = 215, 96
    xs = [15, 268, 521, 774]
    y1, y2 = 20, 210
    f.box("up", xs[0], y1, W, H, ["Tải tệp CSV"], "prog")
    f.box("pf", xs[1], y1, W, H, ["Lập hồ sơ cột", "(kiểu, ô trống, mẫu)"], "prog", size=FS - 2)
    f.box("map", xs[2], y1, W, H, ["AI đề xuất", "ý nghĩa từng cột"], "ai", size=FS - 2)
    f.box("g1", xs[3], y1, W, H, ["Kiểm duyệt 1:", "xác nhận các cột"], "human", size=FS - 2)
    for a, b in (("up", "pf"), ("pf", "map"), ("map", "g1")):
        f.arrow([f.right(a), f.left(b)])
    f.box("imp", xs[0], y2, W, H, ["Che thông tin,", "nhập vào kho"], "prog", size=FS - 2)
    f.box("tax", xs[1], y2, W, H, ["Áp dụng bộ chủ đề", "(AI gợi ý)"], "human", size=FS - 2)
    f.box("cls", xs[2], y2, W, H, ["Phân loại,", "tạo véc-tơ"], "ai", size=FS - 2)
    f.box("clu", xs[3], y2, W, H, ["Phân cụm,", "tính biến động"], "ai", size=FS - 2)
    gx, gy = f.bot("g1")
    mid = (y1 + H + y2) / 2
    f.arrow([(gx, gy), (gx, mid), (f.top("imp")[0], mid), f.top("imp")])
    for a, b in (("imp", "tax"), ("tax", "cls"), ("cls", "clu")):
        f.arrow([f.right(a), f.left(b)])
    # uncategorized loop
    y3 = 410
    f.box("unc", xs[1] + 120, y3, 380, H, ["Chủ đề dưới ngưỡng 0,60: vào nhóm", "chưa phân loại, AI gợi ý chủ đề mới"], "ai", size=FS - 2)
    cx, cy = f.bot("cls")
    f.arrow([(cx, cy), (cx, y3)])
    ux, uy = f.left("unc")
    tx, ty = f.bot("tax")
    f.arrow([(ux, uy), (tx, uy), (tx, ty)], dashed=True)
    f.legend(548, items=("human", "ai", "prog"))
    f.h = 578
    return f


def fig_understand():
    """Hình 3.6 — Vòng điều tra có giới hạn."""
    f = Fig(1000, 800)
    W, H = 330, 84
    A, B = 40, 500
    f.box("q", A, 20, W, H, ["Câu hỏi của người phụ trách", "(đã che thông tin)"], "prog", size=FS - 2)
    f.box("ctx", A, 150, W, H, ["Nạp bối cảnh: trường dữ liệu,", "bộ chủ đề, các cụm"], "prog", size=FS - 2)
    f.box("agg", A, 280, W, H, ["Bước đầu cố định:", "đếm theo chủ đề"], "prog", size=FS - 2)
    f.box("plan", B, 150, W, H, ["Chọn bước tra cứu", "tiếp theo"], "ai", size=FS - 2)
    f.box("run", B, 280, W, H, ["Chạy công cụ,", "ghi bằng chứng"], "prog", size=FS - 2)
    f.box("ev", B, 410, W, H, ["Đánh giá:", "đã đủ bằng chứng chưa?"], "ai", size=FS - 2)
    f.box("syn", B, 560, W, H, ["Tổng hợp nhận định"], "ai", size=FS - 2)
    f.box("g2", B, 690, W, H, ["Kiểm duyệt 2:", "người phụ trách duyệt"], "human", size=FS - 2)
    f.box("end", A, 690, W, H, ["Lưu quyết định,", "kết thúc lượt"], "prog", size=FS - 2)
    f.arrow([f.bot("q"), f.top("ctx")])
    f.arrow([f.bot("ctx"), f.top("agg")])
    f.arrow([f.right("agg"), f.left("run")])
    f.arrow([f.bot("plan"), f.top("run")])
    f.arrow([f.bot("run"), f.top("ev")])
    f.arrow([f.bot("ev"), f.top("syn")])
    f.text(f.bot("ev")[0] + 14, 522, "đủ, hoặc chạm giới hạn", size=FS - 4, anchor="start", style="italic", halo=True)
    f.arrow([f.bot("syn"), f.top("g2")])
    # loop: not enough -> plan
    rx, ry = f.right("ev")
    px, py = f.right("plan")
    f.arrow([(rx, ry), (rx + 45, ry), (rx + 45, py), (px, py)])
    f.text(rx + 55, (ry + py) / 2, "chưa đủ", size=FS - 4, anchor="start", style="italic")
    # investigate more
    gx, gy = f.right("g2")
    f.arrow([(gx, gy), (gx + 150, gy), (gx + 150, py - 22), (px, py - 22)], dashed=True)
    f.text(gx + 52, 600, "điều tra", size=FS - 4, anchor="start", style="italic")
    f.text(gx + 52, 626, "thêm", size=FS - 4, anchor="start", style="italic")
    f.arrow([f.left("g2"), f.right("end")])
    f.text((A + W + B) / 2, 712, "duyệt, sửa,", size=FS - 4, style="italic", halo=True)
    f.text((A + W + B) / 2, 760, "từ chối", size=FS - 4, style="italic", halo=True)
    f.text(A, 470, "Giới hạn do chương trình kiểm tra:", size=FS - 3, anchor="start", weight="bold")
    f.text(A, 500, "tối đa 8 vòng, 18 lời gọi mô hình;", size=FS - 3, anchor="start")
    f.text(A, 528, "không lặp lại bước đã chạy.", size=FS - 3, anchor="start")
    f.h = 830
    f.legend(812, items=("human", "ai", "prog"))
    f.h = 840
    return f


def fig_act():
    """Hình 3.7 — Luồng bước Hành động."""
    f = Fig(1000, 560)
    W, H = 400, 86
    A, B = 30, 560
    f.text(A + W / 2, 24, "Sinh phương án", size=FS, weight="bold")
    f.text(B + W / 2, 24, "Quyết định và theo dõi", size=FS, weight="bold")
    f.box("ins", A, 55, W, H, ["Nhận định đã duyệt"], "prog")
    f.box("gen", A, 185, W, H, ["AI soạn phương án từ bằng chứng", "và thư viện thực hành"], "ai", size=FS - 2)
    f.box("chk", A, 315, W, H, ["Kiểm tra căn cứ hợp lệ,", "tính điểm ưu tiên"], "prog", size=FS - 2)
    f.box("err", A + 60, 445, W - 120, 70, ["Báo lỗi, giữ nguyên dữ liệu"], "prog", size=FS - 3)
    f.box("g3", B, 55, W, H, ["Kiểm duyệt 3: chọn, sửa", "hoặc từ chối phương án"], "human", size=FS - 2)
    f.box("log", B, 185, W, H, ["Ghi nhật ký quyết định,", "tính lại điểm theo giá trị người sửa"], "prog", size=FS - 2)
    f.box("imp", B, 315, W, H, ["Quan sát trước – sau 7 ngày", "(chưa có màn hình)"], "ext", size=FS - 2)
    f.arrow([f.bot("ins"), f.top("gen")])
    f.arrow([f.bot("gen"), f.top("chk")])
    f.arrow([f.bot("chk"), f.top("err")])
    f.text(f.bot("chk")[0] + 12, 428, "căn cứ sai", size=FS - 4, anchor="start", style="italic", halo=True)
    cx, cy = f.right("chk")
    gx, gy = f.left("g3")
    mx = (A + W + B) / 2
    f.arrow([(cx, cy), (mx, cy), (mx, gy), (gx, gy)])
    f.text(A + W + 10, cy - 18, "hợp lệ", size=FS - 4, anchor="start", style="italic", halo=True)
    f.arrow([f.bot("g3"), f.top("log")])
    f.arrow([f.bot("log"), f.top("imp")], dashed=True)
    f.text(f.bot("log")[0] + 12, 296, "phương án đã chấp nhận", size=FS - 4, anchor="start", style="italic", halo=True)
    f.legend(562, items=("human", "ai", "prog"))
    f.h = 592
    return f


FIGS = {
    "fig31_process": fig_process,
    "fig32_usecase": fig_usecase,
    "fig33_arch": fig_arch,
    "fig34_data": fig_data,
    "fig35_listen": fig_listen,
    "fig36_understand": fig_understand,
    "fig37_act": fig_act,
}

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def render(outdir, only=None):
    os.makedirs(outdir, exist_ok=True)
    prof = os.path.join(outdir, "_chrome_profile")
    for name, fn in FIGS.items():
        if only and name not in only:
            continue
        f = fn()
        page = (
            "<!doctype html><html><head><meta charset='utf-8'><style>html,body{margin:0;padding:0;"
            "background:#fff;overflow:hidden}</style></head><body>" + f.svg() + "</body></html>"
        )
        hp = os.path.join(outdir, name + ".html")
        with open(hp, "w", encoding="utf-8") as fh:
            fh.write(page)
        png = os.path.join(outdir, name + ".png")
        cmd = [
            CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            f"--user-data-dir={prof}", "--force-device-scale-factor=2.4",
            f"--window-size={f.w},{f.h}", f"--screenshot={png}",
            "file:///" + hp.replace("\\", "/"),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        print(name, f.w, f.h, "->", png)


if __name__ == "__main__":
    render(sys.argv[1], set(sys.argv[2:]) or None)
