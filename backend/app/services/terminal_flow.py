"""Owner-driven CSV → three human gates → impact, over the public HTTP API."""
from __future__ import annotations

import getpass
import json
import time
import uuid
from pathlib import Path

from app.services.terminal_http import TerminalError


class StopFlow(Exception):
    pass


class PauseFlow(Exception):
    pass


class FlowWizard:
    ID_KEYS = {"product_id", "import_id", "analysis_run_id", "agent_run_id", "insight_id"}

    def __init__(self, client, *, input_fn=input, password_fn=getpass.getpass,
                 output_fn=print, state_path=None, sleep_fn=time.sleep):
        self.client = client
        self.input = input_fn
        self.password = password_fn
        self.output = output_fn
        self.sleep = sleep_fn
        self.state_path = Path(state_path or Path(__file__).resolve().parents[2] / "storage/terminal/session.json")
        self.state = {}

    def ask(self, prompt):
        value = self.input(prompt + " > ").strip()
        if value.lower() in {"/quit", "/exit"}:
            raise StopFlow()
        if value.lower() == "/back":
            raise PauseFlow()
        return value

    def choice(self, prompt, choices, default=None):
        while True:
            value = self.ask(prompt).lower() or default
            if value in choices:
                return value
            self.output("Chọn: " + ", ".join(choices))

    def yes(self, prompt):
        return self.choice(prompt + " [y/N]", {"y", "n"}, "n") == "y"

    def show(self, label, value):
        self.output(label + ":\n" + json.dumps(value, ensure_ascii=False, indent=2, default=str))

    def save(self):
        # Whitelist IDs only; do not serialize prompts, responses, credentials.
        clean = {k: str(uuid.UUID(v)) for k, v in self.state.items() if k in self.ID_KEYS}
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(clean), encoding="utf-8")
        temp.replace(self.state_path)

    def remember(self, key, value):
        self.state[key] = str(uuid.UUID(str(value)))
        self.save()
        self.output(f"{key}={self.state[key]}")

    def load(self):
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.state = {k: str(uuid.UUID(v)) for k, v in data.items() if k in self.ID_KEYS}
        except (OSError, ValueError, AttributeError, TypeError):
            self.state = {}

    def api(self, method, path, **kwargs):
        return self.client.request(method, path, **kwargs)

    def login(self):
        while True:
            email = self.ask("Email đăng nhập")
            password = self.password("Mật khẩu (ẩn): ")
            try:
                user = self.client.login(email, password)
                self.output("Đã đăng nhập; role=" + user["role"])
                return
            except TerminalError as exc:
                self.output(str(exc))
                if exc.status != 401:
                    raise
            finally:
                password = ""

    def choose_product(self):
        products = self.api("GET", "/api/products")["items"]
        for i, product in enumerate(products, 1):
            self.show(str(i), {"id": product["id"], "name": product["name"]})
        choice = self.choice("Chọn product (số) hoặc new để thử riêng CSV", [str(i) for i in range(1, len(products) + 1)] + ["new"])
        if choice == "new":
            name = self.ask("Tên product mới")
            product = self.api("POST", "/api/products", json={"name": name})
        else:
            product = products[int(choice) - 1]
        self.remember("product_id", product["id"])

    def wait(self, path, *, import_job=False):
        started = time.monotonic()
        try:
            while True:
                row = self.api("GET", path)
                state = row.get("status")
                self.output(f"[{state}] {row.get('processed_count', '?')}/{row.get('total_count', '?')} | {int(time.monotonic() - started)}s | Ctrl+C: ngừng chờ")
                if row.get("pending_approval"):
                    return row
                busy = {"mapping_generating", "importing"} if import_job else {"running"}
                if state not in busy:
                    return row
                if time.monotonic() - started > 900:
                    self.output("Đã chờ 15 phút. Giữ ID; có thể tiếp tục kiểm tra sau.")
                    raise PauseFlow()
                self.sleep(2)
        except KeyboardInterrupt:
            self.output("Đã ngừng chờ; job BE vẫn chạy.")
            raise PauseFlow() from None

    def mapping_decisions(self, proposal):
        decisions = []
        for mapping in proposal["mappings"]:
            self.show("Mapping", mapping)
            while True:
                action = self.choice("approve / remap / promote / demote / ignore", ["approve", "remap", "promote", "demote", "ignore"])
                if action == "approve" and mapping["decision"].upper() == "AMBIGUOUS":
                    self.output("AMBIGUOUS: phải chọn mapping cụ thể.")
                    continue
                item = {"source_field": mapping["source_field"], "action": action}
                if action == "remap":
                    item["target_key"] = self.ask("Field đích (ví dụ feedback_text)")
                if action == "promote":
                    item["candidate"] = {"key": self.ask("Field key mới (snake_case)"), "label": self.ask("Label"), "type": self.choice("Kiểu field", ["category", "numeric", "datetime", "text", "boolean"])}
                from app.schemas.import_ import MappingDecisionItem
                from pydantic import ValidationError
                try:
                    MappingDecisionItem.model_validate(item)
                except ValidationError:
                    self.output("Field mới không hợp lệ (key 2–61 ký tự snake_case, label 1–100).")
                    continue
                decisions.append(item)
                break
        return decisions

    def listen(self):
        pid = self.state["product_id"]
        if not self.state.get("import_id"):
            entry = self.ask("Đường dẫn CSV, hoặc id:<import UUID> để tiếp tục").strip('"')
            if entry.startswith("id:"):
                self.remember("import_id", entry[3:].strip())
            else:
                path = Path(entry).expanduser()
                if not path.is_file() or path.suffix.lower() != ".csv":
                    self.output("Không tìm thấy file .csv.")
                    raise PauseFlow()
                with path.open("rb") as stream:
                    row = self.api("POST", "/api/imports", data={"product_id": pid}, files={"file": (path.name, stream, "text/csv")})
                self.remember("import_id", row["id"])
        iid = self.state["import_id"]
        path = f"/api/imports/{iid}"
        row = self.wait(path, import_job=True)
        if row["product_id"] != pid:
            self.state.pop("import_id")
            self.save()
            raise TerminalError("Import không thuộc product đã chọn.")
        if row["status"] == "profile_ready":
            self.show("Preview đã sanitize — chưa gọi AI", self.api("GET", path + "/preview"))
            if not self.yes("Gọi AI đề xuất mapping (tốn token)?"):
                raise PauseFlow()
            self.api("POST", path + "/mapping/proposal")
            row = self.wait(path, import_job=True)
        if row["status"] == "mapping_review":
            self.show("Field có thể map", self.api("GET", f"/api/products/{pid}/schema"))
            proposal = self.api("GET", path + "/mapping")
            decisions = self.mapping_decisions(proposal)
            self.show("Gate #1 — quyết định sẽ gửi", decisions)
            if not self.yes("Chốt Gate #1 và nhập dữ liệu?"):
                raise PauseFlow()
            self.api("POST", path + "/mapping/decision", json={"decisions": decisions})
            row = self.wait(path, import_job=True)
        self.show("Kết quả import", {k: row.get(k) for k in ("id", "status", "row_count", "schema_version", "report")})
        if row["status"] != "imported":
            self.output("Import chưa hoàn tất. Kiểm tra lại hoặc hủy import trước khi nạp file khác.")
            raise PauseFlow()

    def feedbacks(self, path, params=None):
        offset = 0
        while True:
            page = self.api("GET", path, params={**(params or {}), "limit": 20, "offset": offset})
            for item in page["items"]:
                self.show("Feedback", {k: item.get(k) for k in ("id", "feedback_text", "ai_analysis", "has_embedding")})
            offset += len(page["items"])
            if not page["items"] or offset >= page["total"] or not self.yes("Xem trang tiếp?"):
                return

    def analysis(self):
        iid = self.state.get("import_id")
        if not iid:
            self.output("Cần import ID; chọn bước csv trước.")
            raise PauseFlow()
        while True:
            if not self.state.get("analysis_run_id"):
                mode = self.choice("Phân loại: batch / selected / skip", ["batch", "selected", "skip"])
                if mode == "skip":
                    return
                scope = {"import_id": iid, "mode": mode}
                if mode == "selected":
                    self.feedbacks("/api/feedbacks", {"import_id": iid, "analysis_state": "pending"})
                    ids = [str(uuid.UUID(v.strip())) for v in self.ask("Feedback UUID cách nhau dấu phẩy (1–100)").split(",")]
                    if not 1 <= len(ids) <= 100 or len(set(ids)) != len(ids):
                        raise ValueError("Chọn 1–100 ID khác nhau.")
                    scope["feedback_ids"] = ids
                preview = self.api("POST", "/api/analysis/runs/preview", json=scope)
                self.show("Cost preview (ước tính token, không phải giá tiền)", preview)
                if not preview["selected_count"]:
                    self.output("Không còn phản hồi đủ điều kiện.")
                    return
                if not self.yes("Bắt đầu classify + embedding?"):
                    return
                created = self.api("POST", "/api/analysis/runs", json={**scope, "confirmed_item_count": preview["selected_count"]})
                self.remember("analysis_run_id", created["run_id"])
            rid = self.state["analysis_run_id"]
            row = self.wait(f"/api/analysis/runs/{rid}")
            if row.get("import_id") != iid:
                raise TerminalError("Run không thuộc import đã chọn. Sửa lại ID của phiên.")
            self.show("Kết quả run", {k: row.get(k) for k in ("status", "processed_count", "total_count", "failed_count")})
            self.feedbacks(f"/api/analysis/runs/{rid}/results")
            fid = self.ask("Xem similar: nhập feedback UUID, Enter bỏ qua")
            if fid:
                fid = str(uuid.UUID(fid))
                self.show("Phản hồi tương tự", self.api("GET", f"/api/feedbacks/{fid}/similar", params={"k": 5}))
            if not self.yes("Chọn/chạy batch tiếp trong cùng import?"):
                return
            self.state.pop("analysis_run_id", None)
            self.save()

    def understand(self):
        pid = self.state["product_id"]
        self.output("UNDERSTAND phân tích toàn bộ dữ liệu PRODUCT, gồm các import trước đó.")
        while True:
            if not self.state.get("agent_run_id"):
                question = self.ask("Câu hỏi dành cho agent")
                if not 3 <= len(question) <= 2000:
                    self.output("Câu hỏi cần 3–2000 ký tự.")
                    continue
                if not self.yes("Chạy UNDERSTAND (tốn token)?"):
                    return
                created = self.api("POST", "/api/agent/runs", json={"product_id": pid, "question": question})
                self.state.pop("insight_id", None)
                self.remember("agent_run_id", created["run_id"])
            rid = self.state["agent_run_id"]
            row = self.wait(f"/api/agent/runs/{rid}")
            pending = row.get("pending_approval")
            if not pending:
                insights = self.api("GET", "/api/insights", params={"product_id": pid})["items"]
                match = next((i for i in insights if i.get("run_id") == rid), None)
                if match and match["status"] in {"approved", "edited"}:
                    self.remember("insight_id", match["id"])
                    return
                self.output("Run đã kết thúc/chưa có insight được duyệt.")
                if not self.yes("Đặt câu hỏi mới?"):
                    return
                self.state.pop("agent_run_id", None)
                self.state.pop("insight_id", None)
                self.save()
                continue
            scoped = self.api("GET", "/api/insights", params={"product_id": pid})["items"]
            if not any(i["id"] == pending["insight_id"] for i in scoped):
                raise TerminalError("Insight không thuộc product đang chọn hoặc không còn trong danh sách gần đây.")
            self.show("Gate #2 — insight và evidence", pending)
            self.remember("insight_id", pending["insight_id"])
            action = self.choice("approve / edit / investigate_more / reject", ["approve", "edit", "investigate_more", "reject"])
            decision = {"action": action}
            if action == "edit":
                edits = {}
                for key in ("title", "finding"):
                    value = self.ask(key + " mới (Enter giữ nguyên)")
                    if value:
                        edits[key] = value
                decision["edited_insight"] = edits
            decision["reason"] = self.ask("Lý do (Enter bỏ qua)") or None
            result = self.api("POST", f"/api/agent/runs/{rid}/decision", json=decision)
            self.show("Quyết định Gate #2", result)
            if action == "investigate_more":
                continue
            if action == "reject":
                self.state.pop("insight_id", None)
                self.save()
                if self.yes("Đặt câu hỏi mới?"):
                    self.state.pop("agent_run_id", None)
                    self.save()
                    continue
            return

    def score(self, label, optional=False):
        while True:
            value = self.ask(label + " (1–10)" + (", Enter giữ nguyên" if optional else ""))
            if optional and not value:
                return None
            if value.isdigit() and 1 <= int(value) <= 10:
                return int(value)
            self.output("Điểm phải là số nguyên 1–10.")

    def actions(self):
        insight_id = self.state.get("insight_id")
        if not insight_id:
            self.output("Chưa có insight để chạy ACT.")
            return
        insights = self.api("GET", "/api/insights", params={"product_id": self.state["product_id"]})["items"]
        insight = next((i for i in insights if i["id"] == insight_id), None)
        if not insight or insight["status"] not in {"approved", "edited"}:
            self.output("ACT chỉ dành cho insight đã approve/edit. Quay lại Gate #2.")
            return
        path = f"/api/insights/{insight_id}/actions"
        portfolio = self.api("GET", path)
        if not portfolio["items"] and self.yes("Chạy ACT tạo đề xuất (tốn token)?"):
            self.show("ACT", self.api("POST", path + "/generate"))
            portfolio = self.api("GET", path)
        self.show("Ma trận impact–effort", portfolio.get("matrix", {}))
        if not portfolio["items"]:
            self.output("ACT chưa có đề xuất. Có thể thêm thủ công hoặc sang báo cáo.")
        for item in portfolio["items"]:
            self.show("Gate #3 — điểm AI và human", item)
            action = self.choice("accept / reject / edit / skip", ["accept", "reject", "edit", "skip"])
            if action == "skip":
                continue
            patch = {}
            if action == "edit":
                for key in ("recommendation", "rationale"):
                    value = self.ask(key + " mới (Enter giữ nguyên)")
                    if value:
                        patch[key] = value
                for key in ("impact", "effort", "urgency"):
                    value = self.score(key, optional=True)
                    if value is not None:
                        patch[key] = value
                reason = ""
                while not reason:
                    reason = self.ask("Lý do sửa (bắt buộc)")
                patch["override_reason"] = reason
            else:
                patch["status"] = "accepted" if action == "accept" else "rejected"
            self.show("Action sau quyết định", self.api("PATCH", f"/api/actions/{item['id']}", json=patch))
        while self.yes("Thêm action thủ công?"):
            from app.models.enums import BusinessFunction
            functions = [f.value.lower() for f in BusinessFunction]
            body = {"function": self.choice("Business function", functions).upper(), "recommendation": self.ask("Recommendation"), "rationale": self.ask("Rationale")}
            for key in ("impact", "effort", "urgency"):
                body[key] = self.score(key)
            self.show("Action thủ công", self.api("POST", path, json=body))

    def reports(self):
        self.show("ID của phiên (quyết định/kết quả được lưu trên BE)", self.state)
        days = self.choice("Summary TOÀN HỆ THỐNG: 7 / 30 / 90 ngày [30]", ["7", "30", "90"], "30")
        self.show("Summary — toàn hệ thống", self.api("GET", "/api/reports/summary", params={"days": int(days)}))
        self.show("KPI — toàn hệ thống", self.api("GET", "/api/reports/kpis"))
        if self.state.get("insight_id"):
            self.show("Actions cuối phiên", self.api("GET", f"/api/insights/{self.state['insight_id']}/actions"))
        if self.yes("Đo impact cho product đã chọn?"):
            result = self.api("POST", "/api/impact-checks/run", json={"product_id": self.state["product_id"]})
            self.show("Impact check", result)
            if not result["results"]:
                self.output(f"Không có phép đo mới: chưa có action đủ điều kiện ({result['window_days']} ngày), hoặc các action đủ tuổi đã được đo. Không giả lập tác động.")

    def resume_menu(self):
        self.show("ID đang lưu", self.state)
        stage = self.choice("Tiếp tục: csv / analysis / understand / actions / reports / ids / new / question / cancel / quit", ["csv", "analysis", "understand", "actions", "reports", "ids", "new", "question", "cancel", "quit"])
        if stage == "quit":
            raise StopFlow()
        if stage == "ids":
            self.output("Nhập ID từ phiên trước; Enter giữ nguyên. Không tự gửi lại yêu cầu ghi.")
            for key in ("import_id", "analysis_run_id", "agent_run_id", "insight_id"):
                value = self.ask(key)
                if value:
                    self.remember(key, value)
            return None
        if stage in {"new", "question"}:
            keys = self.ID_KEYS - {"product_id"} if stage == "new" else {"agent_run_id", "insight_id"}
            for key in keys:
                self.state.pop(key, None)
            self.save()
            return "csv" if stage == "new" else "understand"
        if stage == "cancel":
            kind = self.choice("Hủy import hoặc analysis (agent không có cancel API)", ["import", "analysis"])
            key = "import_id" if kind == "import" else "analysis_run_id"
            if self.state.get(key) and self.yes("Gửi yêu cầu hủy " + self.state[key] + "?"):
                prefix = "/api/imports" if kind == "import" else "/api/analysis/runs"
                self.show("Hủy", self.api("POST", f"{prefix}/{self.state[key]}/cancel"))
            return None
        return stage

    def run(self):
        self.output("HAPPYNEST — CSV → Gate #1 → phân loại/embedding → UNDERSTAND → Gate #2 → ACT → Gate #3 → báo cáo")
        self.output("/quit: thoát; /back: chọn bước. Không tự duyệt gate hoặc tự chạy AI.")
        stages = ["csv", "analysis", "understand", "actions", "reports"]
        handlers = [self.listen, self.analysis, self.understand, self.actions, self.reports]
        try:
            self.login()
            self.load()
            if self.state.get("product_id") and self.yes("Tiếp tục phiên đã lưu?"):
                self.api("GET", f"/api/products/{self.state['product_id']}")
                stage = None
            else:
                self.state = {}
                self.choose_product()
                stage = "csv"
            while True:
                try:
                    if stage is None:
                        stage = self.resume_menu()
                        continue
                    index = stages.index(stage)
                    handlers[index]()
                    if index == len(stages) - 1:
                        self.output("Đã đi hết flow. Có thể mở lại bằng cùng lệnh để tiếp tục kiểm tra.")
                        break
                    stage = stages[index + 1]
                except (PauseFlow, KeyboardInterrupt):
                    stage = None
                except TerminalError as exc:
                    self.output(f"[HTTP {exc.status or '?'}] {exc}")
                    if exc.status == 401:
                        self.login()
                    stage = None
                except (ValueError, OSError):
                    self.output("Giá trị/UUID hoặc file không hợp lệ. Kiểm tra lại đầu vào.")
                    stage = None
        except (StopFlow, PauseFlow, EOFError, KeyboardInterrupt):
            self.output("Đã thoát; ID đã lưu, job BE không bị tự động hủy.")
