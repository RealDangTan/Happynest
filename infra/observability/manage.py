"""Local operator entrypoint. Credentials stay in backend/.env and child env."""

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
HERE = Path(__file__).resolve().parent
TOOLS = ROOT / ".tools" / "observability"
CLOUD_KEYS = ("GRAFANA_CLOUD_METRICS_URL", "GRAFANA_CLOUD_METRICS_USER", "GRAFANA_CLOUD_LOGS_URL", "GRAFANA_CLOUD_LOGS_USER", "GRAFANA_CLOUD_TOKEN")


def environment():
    values = {key: value for key, value in dotenv_values(BACKEND / ".env").items() if value is not None}
    env = dict(os.environ)
    env.update(values)
    env["HAPPYNEST_METRICS_TARGET"] = "127.0.0.1:8000"
    env["HAPPYNEST_INSTANCE"] = "happynest-local" if env.get("APP_ENV", "dev") != "prod" else "happynest-vps"
    log_dir = Path(env.get("OBSERVABILITY_LOG_DIR", "storage/observability"))
    if not log_dir.is_absolute():
        log_dir = BACKEND / log_dir
    env["HAPPYNEST_LOG_PATH"] = (log_dir / "events.jsonl").as_posix()
    env["HAPPYNEST_RUNTIME"] = (HERE / ".runtime").as_posix()
    env["HAPPYNEST_DASHBOARD_DIR"] = (HERE / "dashboards").as_posix()
    return env


def binary(name):
    pattern = {"alloy": "alloy-windows-amd64.exe", "k6": "k6.exe", "prometheus": "prometheus.exe", "loki": "loki-windows-amd64.exe", "grafana": "grafana.exe"}[name]
    matches = list(TOOLS.rglob(pattern))
    if not matches:
        raise SystemExit("Run infra/observability/install-windows.ps1 first.")
    return str(matches[0])


def configure():
    path = BACKEND / ".env"
    if not path.exists():
        raise SystemExit("Create backend/.env from .env.example and fill the existing app settings first.")
    values = dotenv_values(path)
    if not values.get("METRICS_TOKEN"):
        set_key(path, "METRICS_TOKEN", secrets.token_urlsafe(32))
    if not values.get("OBSERVABILITY_LOG_DIR"):
        set_key(path, "OBSERVABILITY_LOG_DIR", "storage/observability")
    for key in ("GRAFANA_CLOUD_URL", *CLOUD_KEYS):
        if key not in values:
            set_key(path, key, "")
    print("Local metrics token configured in backend/.env (value hidden).")


def status(env):
    result = {"cloud_configured": all(env.get(key) for key in CLOUD_KEYS), "metrics_token_configured": bool(env.get("METRICS_TOKEN"))}
    for name, url in (("backend", "http://127.0.0.1:8000/api/health"), ("collector", "http://127.0.0.1:12345/-/ready"), ("grafana", "http://127.0.0.1:3001/api/health"), ("prometheus", "http://127.0.0.1:9090/-/ready"), ("loki", "http://127.0.0.1:3100/ready")):
        try:
            with urlopen(url, timeout=5) as response:
                if name == "backend":
                    body = json.load(response)
                    result[name] = {key: body.get(key) for key in ("status", "db", "pii_mode")}
                else:
                    result[name] = "ready" if response.status == 200 else "not_ready"
        except (URLError, TimeoutError):
            result[name] = "not_running"
    try:
        request = Request("http://127.0.0.1:8000/metrics", headers={"Authorization": "Bearer " + env.get("METRICS_TOKEN", "")})
        with urlopen(request, timeout=10) as response:
            result["scrape"] = "ok" if b"happynest_http_requests_total" in response.read() else "missing_metrics"
    except (HTTPError, URLError, TimeoutError):
        result["scrape"] = "unavailable"
    print(json.dumps(result, indent=2))


def local_start(env):
    runtime = HERE / ".runtime"
    runtime.mkdir(exist_ok=True)
    password_path = runtime / "grafana-admin-password.txt"
    if not password_path.exists():
        password_path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    env.update({
        "GF_SERVER_HTTP_ADDR": "127.0.0.1", "GF_SERVER_HTTP_PORT": "3001",
        "GF_SERVER_ROOT_URL": "http://127.0.0.1:3001/",
        "GF_AUTH_ANONYMOUS_ENABLED": "true", "GF_AUTH_ANONYMOUS_ORG_ROLE": "Viewer",
        "GF_USERS_ALLOW_SIGN_UP": "false", "GF_SECURITY_ADMIN_PASSWORD": password_path.read_text(encoding="utf-8"),
        "GF_PATHS_DATA": str(runtime / "grafana"), "GF_PATHS_LOGS": str(runtime / "grafana-logs"),
        "GF_PATHS_PLUGINS": str(runtime / "grafana-plugins"), "GF_PATHS_PROVISIONING": str(HERE / "provisioning"),
        "GF_ANALYTICS_REPORTING_ENABLED": "false", "GF_ANALYTICS_CHECK_FOR_UPDATES": "false",
        "GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES": "false",
    })
    services = [
        ("prometheus", 9090, [binary("prometheus"), "--config.file=" + str(HERE / "prometheus.yml"), "--web.listen-address=127.0.0.1:9090", "--web.enable-remote-write-receiver", "--storage.tsdb.path=" + str(runtime / "prometheus"), "--storage.tsdb.retention.time=3d", "--storage.tsdb.retention.size=256MB"]),
        ("loki", 3100, [binary("loki"), "-config.file=" + str(HERE / "loki.yml"), "-config.expand-env=true"]),
        ("grafana", 3001, [binary("grafana"), "server", "--homepath=" + str(Path(binary("grafana")).parent.parent)]),
        ("backend", 8000, [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"]),
        ("alloy", 12345, [binary("alloy"), "run", "--server.http.listen-addr=127.0.0.1:12345", "--storage.path=" + str(runtime / "alloy-local"), str(HERE / "windows-local.alloy")]),
    ]
    import socket

    pid_path = runtime / "processes.json"
    owned = json.loads(pid_path.read_text()) if pid_path.exists() else {}
    for name, port, command in services:
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                print(f"{name}: port {port} already listening; existing process preserved.")
                continue
        with (runtime / f"{name}.out.log").open("ab") as out, (runtime / f"{name}.err.log").open("ab") as err:
            process = subprocess.Popen(command, cwd=BACKEND, env=env, stdout=out, stderr=err,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        owned[name] = {"pid": process.pid, "executable": command[0]}
        print(f"{name}: started PID {process.pid} on loopback port {port}.")
    pid_path.write_text(json.dumps(owned, indent=2), encoding="utf-8")
    print("Dashboard: http://127.0.0.1:3001/d/happynest-operations")


def local_stop():
    # Stop only recorded processes whose executable still matches; never stop an
    # unrelated server that was already running when local-start was invoked.
    path = HERE / ".runtime" / "processes.json"
    if not path.exists():
        print("No owned observability processes recorded.")
        return
    for name, record in json.loads(path.read_text()).items():
        process_id = int(record["pid"])
        expected = str(Path(record["executable"]).resolve())
        roots = (TOOLS.resolve(), (BACKEND / ".venv").resolve())
        if not any(Path(expected).is_relative_to(root) for root in roots):
            raise SystemExit("Recorded executable is outside the managed tool/venv directories.")
        quoted = expected.replace("'", "''")
        command = f"$p = Get-CimInstance Win32_Process -Filter 'ProcessId = {process_id}'; if ($p -and $p.ExecutablePath -eq '{quoted}') {{ Stop-Process -Id {process_id}; Write-Output 'Stopped {name}' }}"
        subprocess.run(["powershell", "-NoProfile", "-Command", command], check=True)
    path.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=("configure", "backend", "alloy", "benchmark", "status", "validate", "local-start", "local-stop"))
    args = parser.parse_args()
    if args.target == "configure":
        configure()
        return
    env = environment()
    if args.target == "local-start":
        local_start(env)
        return
    if args.target == "local-stop":
        local_stop()
        return
    if args.target == "status":
        status(env)
        return
    if args.target == "backend":
        command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"]
    elif args.target in {"alloy", "validate"}:
        if args.target == "alloy":
            missing = [key for key in CLOUD_KEYS if not env.get(key)]
            if missing:
                raise SystemExit("Fill backend/.env before starting cloud collection: " + ", ".join(missing))
            if not env.get("METRICS_TOKEN"):
                raise SystemExit("Run start.ps1 -Target configure first.")
        else:
            # Syntax validation only; these non-routable endpoints are never run.
            env.setdefault("METRICS_TOKEN", "validation-only")
            for key in CLOUD_KEYS:
                if not env.get(key):
                    env[key] = "https://example.invalid/ingest" if key.endswith("URL") else "validation-only"
        config = HERE / ("windows.alloy" if os.name == "nt" else "linux.alloy")
        runtime = HERE / ".runtime"
        runtime.mkdir(exist_ok=True)
        command = [binary("alloy"), "validate", str(config)] if args.target == "validate" else [
            binary("alloy"), "run", "--server.http.listen-addr=127.0.0.1:12345",
            "--storage.path=" + str(runtime), str(config),
        ]
    else:
        output = ROOT / "docs" / "evidence" / "observability"
        output.mkdir(parents=True, exist_ok=True)
        env["K6_SUMMARY_PATH"] = str(output / "k6-api-summary.json")
        env["HAPPYNEST_BASE_URL"] = "http://127.0.0.1:8000"
        command = [binary("k6"), "run", str(HERE / "api-smoke.js")]
    raise SystemExit(subprocess.call(command, cwd=BACKEND, env=env))


if __name__ == "__main__":
    main()
