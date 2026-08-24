"""Launch the full VicinusAI stack with one command.

Boots the TurboFieldfareServer (Swift) on :8080 and the Flask web console
on :5001, then supervises both until interrupted.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import __version__

IS_MACOS = sys.platform == "darwin"


def default_model_dir() -> Path:
    env = os.environ.get("VICINUS_MODEL_DIR")
    if env:
        return Path(env).expanduser()
    if IS_MACOS:
        base = Path.home() / "Library" / "Application Support" / "VicinusAI"
    else:
        base = Path.home() / ".local" / "share" / "vicinus-ai"
    return base / "gemma4.gturbo"


def find_tool(name: str) -> Path | None:
    found = shutil.which(name)
    return Path(found) if found else None


def model_installed(path: Path) -> bool:
    return path.is_dir() and (path / "manifest.json").is_file()


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((host, port)) == 0


def ensure_model(model_path: Path, skip_download: bool) -> bool:
    if model_installed(model_path):
        return True
    repack = find_tool("TurboFieldfareRepack")
    if skip_download or repack is None:
        return False
    model_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"📥 No installed model at {model_path}")
    print("⬇️  Downloading Gemma 4 (~15 GB, happens once; Ctrl+C cancels)…")
    cmd = [str(repack), "--output", str(model_path), "--overwrite"]
    if subprocess.call(cmd) != 0:
        print("↩️  Resuming interrupted download…")
        if subprocess.call(cmd + ["--resume"]) != 0:
            return False
    return model_installed(model_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vicinus-ai",
        description="VicinusAI console: TurboFieldfare inference server + web UI",
    )
    parser.add_argument(
        "--version", action="version", version=f"vicinus-ai {__version__}"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="web UI bind host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--flask-port",
        type=int,
        default=int(os.environ.get("FLASK_PORT", "5001")),
        help="web UI port (default: 5001)",
    )
    parser.add_argument(
        "--turbo-port", type=int, default=8080, help="inference server port"
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=None,
        help="path to an installed .gturbo model directory",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="never auto-download the model; fall back to simulated mode",
    )
    parser.add_argument(
        "--no-turbo",
        action="store_true",
        help="skip the Swift inference server entirely (simulated mode)",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="let the web backend own the inference server so settings "
        "saves can reload the model with new runtime flags",
    )
    return parser


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    args = build_parser().parse_args(argv)
    children: list[tuple[str, subprocess.Popen]] = []
    turbo: subprocess.Popen | None = None

    def terminate_all() -> None:
        for _, proc in children:
            if proc.poll() is None:
                proc.terminate()
        deadline = time.time() + 10
        for _, proc in children:
            try:
                proc.wait(timeout=max(0.1, deadline - time.time()))
            except subprocess.TimeoutExpired:
                proc.kill()

    def on_signal(signum, _frame) -> None:
        raise KeyboardInterrupt

    # Explicit handlers: python.org framework builds can swallow the default
    # SIGINT disposition when launched without a controlling TTY.
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    exit_code = 0
    try:
        print("🚀 Booting VicinusAI …")

        env = os.environ.copy()
        env["FLASK_PORT"] = str(args.flask_port)
        env.setdefault("TURBO_BASE_URL", f"http://127.0.0.1:{args.turbo_port}")
        env.setdefault("TURBO_PORT", str(args.turbo_port))

        if not args.no_turbo:
            server_bin = find_tool("TurboFieldfareServer")
            model_path = (args.model or default_model_dir()).expanduser()
            model_ok = (
                ensure_model(model_path, args.skip_download)
                if server_bin is not None
                else False
            )
            if args.dev and server_bin is not None and model_ok:
                print(
                    "🧠 Dev mode: the web backend owns the inference server "
                    "(settings saves reload it)."
                )
                env["VICINUS_MANAGE_TURBO"] = "1"
                env["TURBO_SERVER_BIN"] = str(server_bin)
                env["VICINUS_MODEL_PATH"] = str(model_path)
            elif server_bin is None:
                print("⚠️  TurboFieldfareServer not on PATH — simulated mode.")
            elif model_ok:
                print(f"🧠 Starting TurboFieldfareServer on :{args.turbo_port} …")
                turbo = subprocess.Popen(
                    [
                        str(server_bin),
                        "--model",
                        str(model_path),
                        "--port",
                        str(args.turbo_port),
                    ]
                )
                children.append(("turbo", turbo))
            else:
                print(f"⚠️  Model unavailable at {model_path} — simulated mode.")
                print("    Re-run without --skip-download or set VICINUS_MODEL_DIR.")

        print(f"💬 Starting the web console on :{args.flask_port} …")
        chat = subprocess.Popen([sys.executable, "-m", "vicinusai.app"], env=env)
        children.append(("web", chat))

        deadline = time.time() + 30
        while time.time() < deadline:
            if port_open(args.flask_port):
                break
            if chat.poll() is not None:
                raise RuntimeError(
                    f"web console exited with code {chat.returncode}"
                )
            time.sleep(0.2)
        else:
            raise RuntimeError("web console did not open its port in time")

        print(f"\n✨ AI server ready at http://localhost:{args.flask_port}")
        print("   The UI flips from Simulated to Live once inference responds.")
        print("🛑 Press Ctrl+C to stop all servers.")

        while True:
            time.sleep(1.0)
            for name, proc in list(children):
                if proc.poll() is not None:
                    if name == "turbo":
                        print("⚠️  Inference server exited — continuing in "
                              "simulated mode.")
                        children.remove((name, proc))
                        turbo = None
                    else:
                        raise RuntimeError(
                            f"{name} server exited unexpectedly "
                            f"(code {proc.returncode})"
                        )
    except KeyboardInterrupt:
        print("\n⏳ Shutting down …")
    except (RuntimeError, OSError) as exc:
        print(f"\n❌ {exc}", file=sys.stderr)
        exit_code = 1
    finally:
        terminate_all()
        print("👋 All services stopped.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
