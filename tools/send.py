#!/usr/bin/env python3
"""Pocket Reader uploader and device manager.

The device listens at `http://pocketreader.local/` (mDNS) or at the IP address
shown on its screen.  This script uploads books, lists them, deletes them,
configures Wi-Fi, reads status and reboots if needed.  **It uses only the
Python standard library.**

    python3 send.py kitap.epr                  # upload a single file
    python3 send.py --list                     # list the books
    python3 send.py --status                   # battery / memory / uptime
    python3 send.py --rm kitap.epr --yes       # delete
    python3 send.py --wifi Evim sifre123       # save Wi-Fi
    python3 send.py --dir ~/kitaplar/          # convert + upload every .epub in the folder
    python3 send.py kitap.epr --watch          # re-upload as the file changes

If mDNS does not work (it fails on some networks/on Windows), pass the IP shown
on the device screen with `--ip 192.168.1.42`.
"""

from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

# Use epub2epr.py as a module (we do not rewrite the conversion).
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import epub2epr
except ImportError:  # pragma: no cover - broken installation
    epub2epr = None  # type: ignore[assignment]

__all__ = ["Device", "DeviceError", "main"]

DEFAULT_HOST = "pocketreader.local"
DEFAULT_PORT = 80
DEFAULT_TIMEOUT = 30.0
CHUNK = 16 * 1024
# A reasonable upper bound for /books on the ESP32-C3's typical 4 MB flash.
DEFAULT_MAX_UPLOAD = 8 * 1024 * 1024


class DeviceError(Exception):
    """A user-displayable error that occurs while talking to the device."""


# --- helpers ----------------------------------------------------------------


def human_size(value: int) -> str:
    """1234567 -> '1.18 MiB'."""
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} GiB"


def human_uptime(seconds: int) -> str:
    """125 -> '2m 5s'."""
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def is_ip_literal(host: str) -> bool:
    """Is `host` a numeric IPv4/IPv6 address?"""
    try:
        socket.inet_pton(socket.AF_INET, host)
        return True
    except OSError:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, host)
        return True
    except OSError:
        return False


def resolve_host(host: str, port: int) -> str:
    """Resolve the host name; if mDNS fails, give an understandable error."""
    if is_ip_literal(host):
        return host
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        if host == DEFAULT_HOST:
            raise DeviceError(
                f"Could not resolve '{host}' ({exc.strerror or exc}).\n"
                "  mDNS (.local) only works on the same local network and only if the\n"
                "  operating system supports it.\n"
                "  Fix: read the IP address shown ON THE DEVICE SCREEN and run:\n"
                "      python3 send.py <file> --ip 192.168.1.42\n"
                "  Is the device on the same Wi-Fi network? If no IP shows on the\n"
                "  screen, the device may not be connected to Wi-Fi."
            ) from exc
        raise DeviceError(
            f"Could not resolve '{host}' ({exc.strerror or exc}). "
            f"Check the address or use --ip <address>."
        ) from exc
    except OSError as exc:
        raise DeviceError(f"Network error while resolving '{host}': {exc}") from exc

    if not infos:
        raise DeviceError(f"No address found for '{host}'.")
    return infos[0][4][0]


# --- device -----------------------------------------------------------------


@dataclass
class Device:
    """HTTP access to a single Pocket Reader device."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    timeout: float = DEFAULT_TIMEOUT

    def __post_init__(self) -> None:
        self.host = resolve_host(self.host, self.port)

    @property
    def netloc(self) -> str:
        if (":" in self.host) and not self.host.startswith("["):
            return f"[{self.host}]:{self.port}"  # IPv6
        return f"{self.host}:{self.port}" if self.port != 80 else self.host

    def base_url(self) -> str:
        return f"http://{self.netloc}"

    # -- low level ----------------------------------------------------------

    def _friendly(self, path: str, exc: BaseException) -> DeviceError:
        reason = exc
        if isinstance(exc, urllib.error.URLError):
            reason = exc.reason  # type: ignore[assignment]
        if isinstance(reason, ConnectionRefusedError):
            return DeviceError(
                f"Connection refused ({self.netloc}).\n"
                "  The device may be asleep -- press the power button to wake it,\n"
                "  wait until a page appears on screen, then try again.\n"
                "  The address may also be wrong: verify it with --ip <address>."
            )
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return DeviceError(
                f"Timeout ({self.timeout:.0f} s) -- {self.netloc}{path} did not respond.\n"
                "  The device may be busy (refreshing the screen); try again in a few\n"
                "  seconds."
            )
        if isinstance(reason, socket.gaierror):
            return DeviceError(
                f"Could not resolve '{self.host}'. Pass the IP shown on the device screen with --ip."
            )
        if isinstance(reason, ConnectionResetError):
            return DeviceError(
                "The connection was closed by the device. The file may be too large, or\n"
                "the device restarted during the upload."
            )
        return DeviceError(f"Network error ({self.netloc}{path}): {exc}")

    def request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        timeout: float | None = None,
    ) -> tuple[int, bytes, dict[str, str]]:
        """Send a simple request with a JSON body (use `upload` for uploading)."""
        data: bytes | None = None
        headers: dict[str, str] = {"Accept": "application/json, text/plain, */*"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self.base_url() + path, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                body = resp.read()
                return resp.status, body, dict(resp.headers.items())
        except urllib.error.HTTPError as exc:
            body = exc.read()
            return exc.code, body, dict(exc.headers.items()) if exc.headers else {}
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            raise self._friendly(path, exc) from exc

    def request_json(self, method: str, path: str, payload: Any = None) -> Any:
        """Send the request and return the JSON response; `DeviceError` on failure."""
        status, body, _headers = self.request(method, path, payload)
        if status == 404:
            raise DeviceError(
                f"404 -- {path} does not exist on this device.\n"
                "  The firmware version may not support this endpoint;\n"
                "  open the device's upload page in a browser and try: "
                f"{self.base_url()}/"
            )
        if status >= 400:
            text = body.decode("utf-8", "replace").strip()[:200]
            raise DeviceError(f"Device returned {status} ({path}): {text or '(empty response)'}")
        if not body.strip():
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            snippet = body[:200].decode("utf-8", "replace")
            raise DeviceError(
                f"The device response is not JSON ({path}): {snippet!r}"
            ) from exc

    # -- high level ---------------------------------------------------------

    def ping(self) -> dict[str, Any]:
        """Fetch the / page; checks whether the device is up."""
        status, _body, _h = self.request("HEAD", "/", timeout=min(8.0, self.timeout))
        if status == 405:  # HEAD not supported, try GET
            status, _body, _h = self.request("GET", "/", timeout=min(8.0, self.timeout))
        if status >= 400:
            raise DeviceError(f"Device returned {status} (GET /).")
        return {"status": status}

    def upload(
        self,
        path: str | Path,
        remote_name: str | None = None,
        progress: bool = True,
        timeout: float | None = None,
    ) -> str:
        """Upload the file to the `/upload` endpoint with the `X-Filename` header."""
        p = Path(path)
        try:
            size = p.stat().st_size
        except OSError as exc:
            raise DeviceError(f"Could not read file: {p} ({exc.strerror or exc})") from exc
        if size == 0:
            raise DeviceError(f"File is empty: {p}")

        name = remote_name or p.name
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        conn = http.client.HTTPConnection(
            self.host, self.port, timeout=timeout or max(self.timeout, 60.0)
        )
        try:
            conn.putrequest("POST", "/upload", skip_accept_encoding=True)
            conn.putheader("X-Filename", name)
            conn.putheader("Content-Type", ctype)
            conn.putheader("Content-Length", str(size))
            conn.putheader("Connection", "close")
            conn.endheaders()

            sent = 0
            shown = -1
            with p.open("rb") as fh:
                while True:
                    chunk = fh.read(CHUNK)
                    if not chunk:
                        break
                    conn.send(chunk)
                    sent += len(chunk)
                    if progress:
                        pct = int(100 * sent / size)
                        if pct != shown:
                            shown = pct
                            _progress_line(sent, size)
            if progress:
                _progress_line(sent, size, final=True)

            resp = conn.getresponse()
            body = resp.read()
            status = resp.status
        except (http.client.HTTPException, OSError, socket.timeout) as exc:
            raise self._friendly("/upload", exc) from exc
        finally:
            conn.close()

        text = body.decode("utf-8", "replace").strip()
        if status in (413, 507):
            raise DeviceError(
                f"File is too large for the device ({human_size(size)}).\n"
                "  The device either lacks free space or the request size limit was exceeded.\n"
                "  Upload the books one at a time, and delete unneeded files with --rm."
            )
        if status == 404:
            raise DeviceError(
                "404 -- /upload not found. The firmware may be old; try the device's\n"
                f"upload page in a browser: {self.base_url()}/"
            )
        if status >= 400:
            raise DeviceError(
                f"Upload failed (HTTP {status}): {text or '(empty response)'}"
            )
        return text or f"HTTP {status}"

    def list_books(self) -> list[dict[str, Any]]:
        data = self.request_json("GET", "/list")
        if isinstance(data, dict):  # some firmwares return {"books": [...]}
            data = data.get("books") or data.get("files") or []
        if not isinstance(data, list):
            raise DeviceError(f"/list returned an unexpected response: {type(data).__name__}")
        return [item for item in data if isinstance(item, dict)]

    def delete(self, name: str) -> None:
        self.request_json("POST", "/delete", {"name": name})

    def set_wifi(self, ssid: str, password: str) -> None:
        self.request_json("POST", "/wifi", {"ssid": ssid, "pass": password})

    def status(self) -> dict[str, Any]:
        data = self.request_json("GET", "/status")
        if not isinstance(data, dict):
            raise DeviceError("/status returned an unexpected response.")
        return data

    def reboot(self) -> bool:
        """Run `/reboot` if present.  If the endpoint is missing, say so politely."""
        status, body, _h = self.request("POST", "/reboot", payload=None)
        if status == 404:
            return False
        if status >= 400:
            text = body.decode("utf-8", "replace").strip()[:120]
            raise DeviceError(f"Reboot failed (HTTP {status}): {text}")
        return True


_last_pct_bucket = {"value": -1}


def _progress_line(done: int, total: int, final: bool = False) -> None:
    """Write the progress bar to stderr.

    If not a terminal (log file, CI), it prints one line per 20% instead of a bar.
    """
    ratio = (done / total) if total else 1.0
    pct = int(ratio * 100)

    if not sys.stderr.isatty():
        bucket = pct // 20
        if final:
            sys.stderr.write(f"Uploading: {pct}% done ({human_size(done)})\n")
            sys.stderr.flush()
            return
        if bucket == _last_pct_bucket["value"]:
            return
        _last_pct_bucket["value"] = bucket
        sys.stderr.write(f"Uploading: {pct}%\n")
        sys.stderr.flush()
        return

    width = 28
    filled = max(0, min(width, int(width * ratio)))
    bar = "#" * filled + "." * (width - filled)
    line = (
        f"\rUploading [{bar}] {ratio * 100:5.1f}%  "
        f"{human_size(done)} / {human_size(total)}"
    )
    if final:
        line += "  done\n"
    sys.stderr.write(line)
    sys.stderr.flush()


# --- commands ---------------------------------------------------------------


def cmd_list(dev: Device, as_json: bool = False) -> int:
    books = dev.list_books()
    if as_json:
        print(json.dumps(books, ensure_ascii=False, indent=2))
        return 0
    if not books:
        print("No books on the device. To upload one: python3 send.py kitap.epr")
        return 0
    name_w = max(len(str(b.get("name", ""))) for b in books)
    name_w = min(max(name_w, 16), 40)
    title_w = 32
    header = f"{'NAME':<{name_w}}  {'TITLE':<{title_w}}  {'AUTHOR':<20}  {'SIZE':>9}"
    print(header)
    print("-" * len(header))
    total = 0
    for b in books:
        name = str(b.get("name", ""))[:name_w]
        title = str(b.get("title", "") or "-")[:title_w]
        author = str(b.get("author", "") or "-")[:20]
        size = b.get("size", 0)
        try:
            total += int(size)
        except (TypeError, ValueError):
            size = 0
        print(f"{name:<{name_w}}  {title:<{title_w}}  {author:<20}  {human_size(int(size)):>9}")
    print("-" * len(header))
    print(f"{len(books)} books, total {human_size(total)}")
    return 0


def cmd_status(dev: Device, as_json: bool = False) -> int:
    st = dev.status()
    if as_json:
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return 0

    def g(key: str, default: Any = None) -> Any:
        value = st.get(key, default)
        return default if value is None else value

    pct = g("batt_pct", 0)
    try:
        pct = int(pct)
    except (TypeError, ValueError):
        pct = 0
    filled = max(0, min(20, round(pct / 5)))
    bar = "#" * filled + "." * (20 - filled)

    print(f"Firmware   : {g('fw', '?')}")
    print(f"Battery    : [{bar}] {pct}%  ({g('batt_mv', '?')} mV)")
    print(f"Free heap  : {human_size(int(g('heap', 0)))}")
    print(f"Free space : {human_size(int(g('free', 0)))}")
    print(f"Uptime     : {human_uptime(int(g('uptime', 0)))}")
    extra = {k: v for k, v in st.items() if k not in {"fw", "heap", "free", "batt_mv", "batt_pct", "uptime"}}
    for key, value in extra.items():
        print(f"{key:<10} : {value}")
    return 0


def cmd_delete(dev: Device, name: str, assume_yes: bool) -> int:
    if not assume_yes:
        answer = input(f"Delete '{name}'? [y/N] ").strip().lower()
        if answer not in ("e", "evet", "y", "yes"):
            print("Cancelled.")
            return 1
    dev.delete(name)
    print(f"Deleted: {name}")
    return 0


def cmd_wifi(dev: Device, ssid: str, password: str) -> int:
    try:
        dev.set_wifi(ssid, password)
    except DeviceError as exc:
        if "404" in str(exc):
            raise DeviceError(
                "404 -- /wifi not found. The firmware in this version does not support\n"
                "Wi-Fi setup; configure it from the device's own web page."
            ) from exc
        raise
    print(f"Wi-Fi saved: {ssid}")
    print("The device may restart within a few seconds to connect to the new network.")
    return 0


def cmd_reboot(dev: Device) -> int:
    if dev.reboot():
        print("Rebooting the device…")
        return 0
    print(
        "This firmware version has no /reboot endpoint (404).\n"
        "  Power-cycle the device with its power button."
    )
    return 1


def cmd_upload(
    dev: Device,
    path: Path,
    remote_name: str | None,
    max_upload: int,
    force: bool,
) -> int:
    size = path.stat().st_size
    if size > max_upload and not force:
        answer = input(
            f"WARNING: {path.name} is {human_size(size)} — this may be large for "
            f"the device's flash.\nUpload anyway? [y/N] "
        ).strip().lower()
        if answer not in ("e", "evet", "y", "yes"):
            print("Cancelled.")
            return 1
    message = dev.upload(path, remote_name=remote_name)
    print(f"Uploaded: {remote_name or path.name} ({human_size(size)}) — {message}")
    return 0


def cmd_status_or_hint(exc: DeviceError) -> int:
    print(f"ERROR: {exc}", file=sys.stderr)
    return 2


# --- batch / watch ----------------------------------------------------------


def iter_epubs(folder: Path) -> Iterator[Path]:
    """Yield the .epub files in the folder (excluding subfolders) in alphabetical order."""
    yield from sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".epub")


def convert_one(src: Path, out_dir: Path | None, verbose: bool) -> Path:
    """Convert a single EPUB to .epr using the epub2epr module."""
    if epub2epr is None:
        raise DeviceError(
            "epub2epr.py not found (it must be in the same folder as send.py)."
        )
    dst = (out_dir / (src.stem + ".epr")) if out_dir else src.with_suffix(".epr")
    try:
        out, stats = epub2epr.convert_and_write(src, dst, verify=True, verbose=False)
    except epub2epr.EprError as exc:
        raise DeviceError(f"Could not convert '{src.name}': {exc}") from exc
    if verbose:
        print(f"  converted: {src.name} -> {out.name} ({stats.chapters} chapters)")
    return out


def cmd_batch(
    dev: Device,
    folder: Path,
    out_dir: Path | None,
    keep: bool,
    max_upload: int,
    force: bool,
    verbose: bool,
) -> int:
    if not folder.is_dir():
        raise DeviceError(f"Folder not found: {folder}")
    files = list(iter_epubs(folder))
    if not files:
        print(f"No .epub files in '{folder}'.")
        return 0
    print(f"Found {len(files)} EPUB files.")
    failures = 0
    for src in files:
        try:
            tmp = convert_one(src, out_dir, verbose)
        except DeviceError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            failures += 1
            continue
        try:
            size = tmp.stat().st_size
            if size > max_upload and not force:
                print(
                    f"WARNING: {tmp.name} is too large ({human_size(size)}), skipping. "
                    f"Use --force to override.",
                    file=sys.stderr,
                )
                failures += 1
                continue
            message = dev.upload(tmp)
            print(f"  {tmp.name} ({human_size(size)}) -> {message}")
        except DeviceError as exc:
            print(f"ERROR ({tmp.name}): {exc}", file=sys.stderr)
            failures += 1
        finally:
            if out_dir is None and not keep:
                try:
                    tmp.unlink()
                except OSError:
                    pass
    ok = len(files) - failures
    print(f"Done: {ok} uploaded, {failures} failed.")
    return 0 if failures == 0 else 1


def cmd_watch(
    dev: Device,
    targets: list[Path],
    interval: float,
    verbose: bool,
    convert: bool = False,
    out_dir: Path | None = None,
) -> int:
    """Re-upload files as they change on disk (mtime polling).

    When `convert=True` the watched files are `.epub`: on every change they are
    first converted to `.epr` with `epub2epr`, then uploaded.  Very handy while
    writing a book (fixing the title/paragraphs).
    """
    if not targets:
        raise DeviceError("--watch needs at least one file or --dir.")
    for t in targets:
        if not t.exists():
            raise DeviceError(f"No file to watch: {t}")

    def push(target: Path) -> str:
        src = convert_one(target, out_dir, verbose) if convert else target
        message = dev.upload(src)
        if convert and out_dir is None:
            try:
                src.unlink()
            except OSError:
                pass
        return message

    mtimes = {t: t.stat().st_mtime for t in targets}
    for t in targets:
        try:
            print(f"[initial upload] {t.name} -> {push(t)}")
        except DeviceError as exc:
            print(f"ERROR ({t.name}): {exc}", file=sys.stderr)

    print(f"Watching ({interval:.1f} s), press Ctrl+C to quit …")
    try:
        while True:
            time.sleep(interval)
            for t in targets:
                try:
                    mtime = t.stat().st_mtime
                except OSError:
                    continue
                if mtime == mtimes[t]:
                    continue
                mtimes[t] = mtime
                try:
                    stamp = time.strftime("%H:%M:%S")
                    print(f"[{stamp}] {t.name} changed -> {push(t)}")
                except DeviceError as exc:
                    print(f"ERROR ({t.name}): {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nWatching stopped.")
        return 0


# --- CLI --------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="send.py",
        description=(
            "Upload books to a Pocket Reader and manage the device. "
            "The device is looked up at http://pocketreader.local/ by default."
        ),
        epilog=(
            "Examples:\n"
            "  send.py kitap.epr\n"
            "  send.py kitap.epr --ip 192.168.1.42\n"
            "  send.py --list\n"
            "  send.py --status --json\n"
            "  send.py --rm eski.epr --yes\n"
            "  send.py --wifi EvimAgi sifre123\n"
            "  send.py --dir ~/kitaplar/ -v\n"
            "  send.py kitap.epr --watch --watch-interval 1\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("file", nargs="?", help="the .epr file to upload (or .epub)")
    p.add_argument("--host", default=DEFAULT_HOST, help=f"device address (default: {DEFAULT_HOST})")
    p.add_argument("--ip", help="the IP shown on the device screen; used instead of --host")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"TCP port (default: {DEFAULT_PORT})")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="timeout in seconds (default: 30)")

    actions = p.add_argument_group("device operations")
    actions.add_argument("--list", action="store_true", help="list the books on the device as a table")
    actions.add_argument("--rm", metavar="NAME", help="delete a book from the device")
    actions.add_argument("--wifi", nargs=2, metavar=("SSID", "PASSWORD"), help="save Wi-Fi credentials")
    actions.add_argument("--status", action="store_true", help="battery/memory/uptime information")
    actions.add_argument("--reboot", action="store_true", help="reboot the device (warns if the firmware does not support it)")
    actions.add_argument("--json", action="store_true", help="print the --list/--status output as raw JSON")

    batch = p.add_argument_group("batch operations and watching")
    batch.add_argument("--dir", metavar="FOLDER", help="convert and upload every .epub in the folder")
    batch.add_argument("--out-dir", metavar="FOLDER", help="folder to write the converted .epr files into")
    batch.add_argument("--keep", action="store_true", help="do not delete the intermediate .epr files during a batch conversion")
    batch.add_argument("--watch", action="store_true", help="re-upload as files change (mtime polling)")
    batch.add_argument("--watch-interval", type=float, default=2.0, help="polling interval, seconds (default: 2.0)")

    other = p.add_argument_group("other")
    other.add_argument("--yes", action="store_true", help="do not ask for delete confirmation")
    other.add_argument("--force", action="store_true", help="ignore the large-file warning")
    other.add_argument(
        "--max-upload",
        type=int,
        default=DEFAULT_MAX_UPLOAD,
        metavar="BYTES",
        help=f"warning threshold (default: {DEFAULT_MAX_UPLOAD} bytes)",
    )
    other.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    # Do not allow more than one job at a time.
    chosen = [
        bool(args.file or args.dir),
        bool(args.list),
        bool(args.rm),
        bool(args.wifi),
        bool(args.status),
        bool(args.reboot),
    ]
    if sum(chosen) != 1:
        print(
            "ERROR: choose exactly one job: a file/--dir, --list, --rm, --wifi,\n"
            "      --status or --reboot.  (send.py --help)",
            file=sys.stderr,
        )
        return 2

    try:
        dev = Device(
            host=args.ip or args.host,
            port=args.port,
            timeout=args.timeout,
        )
    except DeviceError as exc:
        return cmd_status_or_hint(exc)

    try:
        if args.list:
            return cmd_list(dev, as_json=args.json)
        if args.status:
            return cmd_status(dev, as_json=args.json)
        if args.rm:
            return cmd_delete(dev, args.rm, args.yes)
        if args.wifi:
            return cmd_wifi(dev, args.wifi[0], args.wifi[1])
        if args.reboot:
            return cmd_reboot(dev)
        if args.dir:
            folder = Path(args.dir).expanduser()
            if args.watch:
                targets = list(iter_epubs(folder)) if folder.is_dir() else []
                if not targets:
                    raise DeviceError(f"No .epub to watch in '{folder}'.")
                return cmd_watch(
                    dev,
                    targets,
                    args.watch_interval,
                    args.verbose,
                    convert=True,
                    out_dir=Path(args.out_dir).expanduser() if args.out_dir else None,
                )
            return cmd_batch(
                dev,
                Path(args.dir).expanduser(),
                Path(args.out_dir).expanduser() if args.out_dir else None,
                args.keep,
                args.max_upload,
                args.force,
                args.verbose,
            )

        assert args.file, "file path required"
        src = Path(args.file).expanduser()
        if not src.exists():
            print(f"ERROR: file not found: {src}", file=sys.stderr)
            return 2
        is_epub = src.suffix.lower() == ".epub"
        if args.watch:
            # While watching an .epub, re-convert on every change; an .epr uploads directly.
            return cmd_watch(
                dev, [src], args.watch_interval, args.verbose, convert=is_epub
            )
        if is_epub:
            src = convert_one(src, None, args.verbose)
        return cmd_upload(dev, src, None, args.max_upload, args.force)
    except DeviceError as exc:
        return cmd_status_or_hint(exc)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
