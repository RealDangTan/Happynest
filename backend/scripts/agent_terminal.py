"""Existing agent terminal; --flow adds the HTTP CSV-to-impact wizard."""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow", action="store_true", help="CSV → three human gates → impact over HTTP")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--session-file", type=Path)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.flow:
        from app.services.terminal_flow import FlowWizard
        from app.services.terminal_http import TerminalClient, TerminalError

        client = TerminalClient(args.base_url)
        try:
            FlowWizard(client, state_path=args.session_file).run()
        except TerminalError as exc:
            print(str(exc))
            return 1
        finally:
            client.close()
        return 0

    from app.services.agent_terminal import RealTerminalRuntime, run_interactive
    from app.services.presidio_service import init_presidio

    print("Loading PII sanitizer (first start may take about one minute)...")
    init_presidio()
    run_interactive(RealTerminalRuntime())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
