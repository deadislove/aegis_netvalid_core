from collections import deque
import time
from rich.console import Console
import os

console = Console()

class AegisCore:
    def __init__(self, config):
        self.config = config
        self.is_inputting = False
        self.running = True
        self.message_log = deque(maxlen=20)
        self._check_privileges()

    def _check_privileges(self):
        if os.getuid() != 0:
            console.print("[bold red]Critical: This tool requires root privileges (sudo) to capture network packets.[/bold red]")

        self.logs = []
        self.log_files = f"outputs/logs/aegis_{int(time.time())}.log"
        os.makedirs(os.path.dirname(self.log_files), exist_ok=True)

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

    def aegis_log(self, message, engine_name="System"):
        """
        Intercom interface for engine calling
        """
        try:
            timestamp = time.strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] [{engine_name}] {message}"
            self.message_log.append(log_entry)

            with open(self.log_files, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Failed to write log: {e}")
        
        # if not self.is_inputting:
        #     console.print(f"[dim][{engine_name}][/dim] {message}")
