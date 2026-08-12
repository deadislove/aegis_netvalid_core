from collections import deque
import threading
import time
import psutil
from rich.console import Console
import os

console = Console()

class AegisCore:
    def __init__(self, config):
        self.config = config
        self.is_inputting = False
        self.running = True
        self.message_log = deque(maxlen=20)
        self._log_lock = threading.Lock()
        self._log_fh = None
        self._process = psutil.Process()
        # cpu_percent() always returns 0.0 on its first call (it needs a
        # baseline to diff against) - prime it here so the first real
        # dashboard read is already meaningful.
        self._process.cpu_percent(interval=None)
        self._check_privileges()

    def _check_privileges(self):
        if os.getuid() != 0:
            console.print("[bold red]Critical: This tool requires root privileges (sudo) to capture network packets.[/bold red]")

        self.logs = []
        self.log_files = f"outputs/logs/aegis_{int(time.time())}.log"
        os.makedirs(os.path.dirname(self.log_files), exist_ok=True)
        # Keep a single handle open for the process lifetime instead of
        # re-opening on every aegis_log() call. Each write is still flushed
        # immediately, so a message is durable on disk (survives the process
        # being killed) the moment aegis_log() returns - this matches the
        # previous open+write+close behavior's durability, just without the
        # repeated open/close syscalls on every message.
        self._log_fh = open(self.log_files, "a", encoding="utf-8")

    def fix_log_permissions(self):
        """
        Return the permissions of the log file to the original user who executed it via sudo.
        """
        try:
            uid = int(os.environ.get('SUDO_UID',os.getuid()))
            gid = int(os.environ.get('SUDO_GID', os.getgid()))

            log_dir = os.path.dirname(self.log_files)
            os.chown(log_dir, uid, gid)

            if os.path.exists(self.log_files):
                os.chown(self.log_files, uid, gid)
        except Exception:
            pass

    def get_self_resource_usage(self):
        """
        CPU/memory usage of the Aegis process itself (not a monitored
        device) - useful since Aegis runs several sniffer/stresser threads
        that can themselves become the bottleneck under load.
        """
        try:
            return {
                "cpu_percent": self._process.cpu_percent(interval=None),
                "memory_mb": self._process.memory_info().rss / (1024 * 1024),
            }
        except Exception:
            return {"cpu_percent": 0.0, "memory_mb": 0.0}

    def close_log(self):
        """
        Flush and close the log file handle. Safe to call multiple times.
        """
        with self._log_lock:
            if self._log_fh and not self._log_fh.closed:
                try:
                    self._log_fh.flush()
                    os.fsync(self._log_fh.fileno())
                except Exception:
                    pass
                self._log_fh.close()

    def aegis_log(self, message, engine_name="System"):
        """
        Intercom interface for engine calling
        """
        try:
            timestamp = time.strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] [{engine_name}] {message}"
            self.message_log.append(log_entry)

            with self._log_lock:
                if self._log_fh and not self._log_fh.closed:
                    self._log_fh.write(log_entry + "\n")
                    self._log_fh.flush()
        except Exception as e:
            print(f"Failed to write log: {e}")

        # if not self.is_inputting:
        #     console.print(f"[dim][{engine_name}][/dim] {message}")
