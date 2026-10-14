"""Build the portable native Grafana dashboard. Uses stock Grafana panels."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
panels = []
metrics = {"type": "prometheus", "uid": "${metrics}"}
logs = {"type": "loki", "uid": "${logs}"}
selection = 'job="happynest-backend",instance=~"$instance"'
requests = 'happynest_http_requests_total{' + selection + ',route=~"$route"}'
duration = 'happynest_http_request_duration_seconds_bucket{' + selection + ',route=~"$route"}'


def panel(title, expression, x, y, w=8, h=7, kind="timeseries", unit="short", description="", legend="__auto"):
    value = {
        "id": len(panels) + 1, "title": title, "type": kind,
        "gridPos": {"x": x, "y": y, "w": w, "h": h}, "datasource": metrics,
        "description": description,
        "fieldConfig": {"defaults": {"unit": unit, "color": {"mode": "palette-classic"}}, "overrides": []},
        "options": {"tooltip": {"mode": "multi"}, "legend": {"displayMode": "list", "placement": "bottom"}},
        "targets": [{"expr": expression, "refId": "A", "legendFormat": legend}],
    }
    if kind == "stat":
        value["options"] = {"reduceOptions": {"calcs": ["lastNotNull"], "values": False}, "colorMode": "value", "graphMode": "area"}
    panels.append(value)
    return value


def row(title, y):
    panels.append({"id": len(panels) + 1, "title": title, "type": "row", "collapsed": False, "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}})


row("API · Server có phản hồi tốt không?", 0)
panel("Backend có được thu thập?", 'up{' + selection + '}', 0, 1, 4, 4, "stat", description="1 = Alloy vừa scrape được API; 0 = scrape thất bại. Đây không phải uptime bên ngoài mạng.")
panel("Request / giây", 'sum(rate(' + requests + '[$__rate_interval]))', 4, 1, 5, 4, "stat", "reqps")
panel("Lỗi server · 5xx", '(100 * (sum(rate(happynest_http_requests_total{' + selection + ',route=~"$route",status_code=~"5.."}[$__rate_interval])) or vector(0)) / sum(rate(' + requests + '[$__rate_interval])))', 9, 1, 5, 4, "stat", "percent", "Tỷ lệ 5xx trên request trong khoảng rate; 4xx được xem riêng ở bảng trạng thái.")
panel("Số mẫu · khoảng đang xem", 'sum(increase(' + requests + '[$__range]))', 14, 1, 5, 4, "stat", description="Từ counter scrape nên số tăng có thể được nội suy; file k6 chứa số request chính xác của thí nghiệm.")
panel("Đang xử lý", 'sum(happynest_http_requests_in_progress{' + selection + '})', 19, 1, 5, 4, "stat")
latency = panel("API latency · p50 / p95 / p99", 'histogram_quantile(0.5, sum by(le)(rate(' + duration + '[$__rate_interval])))', 0, 5, 12, 8, unit="s", legend="p50", description="Kết thúc khi gửi body xong; không gồm background job. Percentile ước lượng từ histogram; p99 với ít mẫu còn thiếu ổn định.")
for ref, quantile in (("B", "0.95"), ("C", "0.99")):
    latency["targets"].append({"expr": 'histogram_quantile(' + quantile + ', sum by(le)(rate(' + duration + '[$__rate_interval])))', "refId": ref, "legendFormat": "p" + str(int(float(quantile) * 100))})
panel("p95 theo endpoint", 'histogram_quantile(0.95, sum by(le,route)(rate(' + duration + '[$__rate_interval])))', 12, 5, 12, 8, unit="s", legend="{{route}}")
panel("HTTP status theo thời gian", 'sum by(status_code)(rate(' + requests + '[$__rate_interval]))', 0, 13, 12, 7, unit="reqps", legend="HTTP {{status_code}}")
panel("Request theo endpoint", 'sum by(route)(rate(' + requests + '[$__rate_interval]))', 12, 13, 12, 7, unit="reqps", legend="{{route}}")

row("Pipeline · LISTEN / UNDERSTAND", 20)
panel("Run trong database · theo trạng thái", 'happynest_pipeline_runs{' + selection + '}', 0, 21, 12, 7, legend="{{pipeline}} · {{status}}", description="Tổng snapshot toàn ứng dụng. running có thể đang chờ HITL; không đồng nghĩa đang dùng CPU.")
panel("Thời gian chạy chủ động · p95", 'histogram_quantile(0.95, sum by(le,pipeline)(rate(happynest_pipeline_execution_duration_seconds_bucket{' + selection + '}[$__rate_interval])))', 12, 21, 12, 7, unit="s", legend="{{pipeline}}", description="LISTEN: mỗi lượt runner. UNDERSTAND: mỗi đoạn graph chạy tới interrupt/kết thúc; loại thời gian giữa hai lần duyệt. Chỉ gồm lượt chạy sau khi bật telemetry.")
panel("Database snapshot còn dùng được?", 'happynest_database_snapshot_available{' + selection + '}', 0, 28, 4, 4, "stat", description="0 = lần đọc snapshot gần nhất lỗi; các count cũ được giữ lại và không nên coi là mới.")
panel("Tuổi snapshot database", 'time() - happynest_database_snapshot_timestamp_seconds{' + selection + '}', 4, 28, 4, 4, "stat", "s")
panel("Feedback đã xử lý · LISTEN", 'happynest_pipeline_processed_feedbacks{' + selection + '}', 8, 28, 4, 4, "stat")
panel("Lượt gọi model / phút", 'sum by(call_type,outcome)(rate(happynest_llm_calls_total{' + selection + '}[$__rate_interval])) * 60', 12, 28, 12, 7, legend="{{call_type}} · {{outcome}}", description="Đếm từng attempt, kể cả retry. Đây không phải số run.")
panel("LLM latency · p95 theo tác vụ", 'histogram_quantile(0.95, sum by(le,call_type)(rate(happynest_llm_call_duration_seconds_bucket{' + selection + '}[$__rate_interval])))', 0, 35, 12, 7, unit="s", legend="{{call_type}}")
panel("Token / phút", 'sum by(direction)(rate(happynest_llm_tokens_total{' + selection + '}[$__rate_interval])) * 60', 12, 35, 12, 7, legend="{{direction}}", description="Usage do provider trả về; không tự suy ra chi phí hóa đơn.")

row("Máy chạy app · Windows hoặc VPS Linux", 42)
host = 'job="happynest-host",instance=~"$instance"'
panel("CPU đang dùng", '100 * (1 - avg by(instance)(rate(windows_cpu_time_total{' + host + ',mode="idle"}[$__rate_interval]))) or 100 * (1 - avg by(instance)(rate(node_cpu_seconds_total{' + host + ',mode="idle"}[$__rate_interval])))', 0, 43, 8, 7, unit="percent", description="CPU của máy đang chạy app/Alloy; không phải CPU Supabase.")
panel("RAM đang dùng", '100 * (1 - windows_memory_available_bytes{' + host + '} / on(instance) windows_memory_physical_total_bytes{' + host + '}) or 100 * (1 - node_memory_MemAvailable_bytes{' + host + '} / node_memory_MemTotal_bytes{' + host + '})', 8, 43, 8, 7, unit="percent")
panel("Đĩa trống", 'windows_logical_disk_free_bytes{' + host + '} or node_filesystem_avail_bytes{' + host + ',fstype!~"tmpfs|overlay"}', 16, 43, 8, 7, unit="bytes", legend="{{volume}}{{mountpoint}}")

row("Log · lọc bằng endpoint hoặc mã request/run", 50)
error_panel = panel("Lỗi và cảnh báo", '', 0, 51, 24, 9, "logs", description="Metadata an toàn; không lưu body, query, cookie, exception message hay locals. Mở dòng để xem request_id/run_id và frames.")
error_panel["datasource"] = logs
error_panel["targets"] = [{"expr": '{service_name="happynest-backend",instance=~"$instance",level=~"ERROR|WARNING"} | json', "refId": "A"}]
error_panel["options"] = {"showTime": True, "showLabels": False, "wrapLogMessage": True, "sortOrder": "Descending", "enableLogDetails": True}
all_logs = panel("Tìm request hoặc run", '', 0, 60, 24, 9, "logs", description="Nhập UUID vào bộ lọc correlation; để trống để xem toàn bộ. ID chỉ là field log, không là metric/Loki label.")
all_logs["datasource"] = logs
all_logs["targets"] = [{"expr": '{service_name="happynest-backend",instance=~"$instance"} |= "$correlation" | json', "refId": "A"}]
all_logs["options"] = error_panel["options"]

dashboard = {
    "uid": "happynest-operations", "title": "HappyNest · Sức khỏe hệ thống", "schemaVersion": 39,
    "version": 1, "editable": False, "tags": ["happynest", "observability"], "timezone": "Asia/Ho_Chi_Minh",
    "refresh": "30s", "time": {"from": "now-30m", "to": "now"},
    "description": "API, pipeline, host và log an toàn. Data source có thể đổi sang Grafana Cloud. Số đo là thực tế; panel chưa có lượt chạy sẽ hiện No data.",
    "templating": {"list": [
        {"name": "metrics", "label": "Metrics", "type": "datasource", "query": "prometheus", "current": {"text": "HappyNest metrics", "value": "happynest-metrics"}},
        {"name": "logs", "label": "Logs", "type": "datasource", "query": "loki", "current": {"text": "HappyNest logs", "value": "happynest-logs"}},
        {"name": "instance", "label": "Máy", "type": "query", "datasource": metrics, "query": 'label_values(up{job="happynest-backend"}, instance)', "refresh": 1, "includeAll": True, "allValue": ".*", "current": {"text": "All", "value": "$__all"}},
        {"name": "route", "label": "Endpoint", "type": "query", "datasource": metrics, "query": 'label_values(happynest_http_requests_total, route)', "refresh": 1, "includeAll": True, "allValue": ".*", "current": {"text": "All", "value": "$__all"}},
        {"name": "correlation", "label": "Request / run UUID", "type": "textbox", "current": {"text": "", "value": ""}},
    ]},
    "links": [{"title": "Langfuse", "url": "https://cloud.langfuse.com", "targetBlank": True}, {"title": "Supabase", "url": "https://supabase.com/dashboard", "targetBlank": True}],
    "panels": panels,
}
directory = HERE / "dashboards"
directory.mkdir(exist_ok=True)
(directory / "happynest.json").write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Built Grafana dashboard with {len(panels)} panels/rows.")
