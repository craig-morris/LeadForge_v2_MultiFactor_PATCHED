import json, os, threading, time


class Checkpoint:
    def __init__(self, directory="checkpoint"):
        self.directory = os.path.abspath(os.path.expanduser(directory))
        self.lock = threading.Lock()
        os.makedirs(self.directory, exist_ok=True)

    def path(self, input_path):
        base = os.path.basename(input_path).replace(".", "_")
        return os.path.join(self.directory, base + "_progress.json")

    def save(self, input_path, state):
        with self.lock:
            p = self.path(input_path)
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"saved": time.time(), **state}, f, indent=2)
            os.replace(tmp, p)

    def load(self, input_path):
        try:
            with open(self.path(input_path), encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def clear(self, input_path):
        try:
            os.remove(self.path(input_path))
        except FileNotFoundError:
            pass
