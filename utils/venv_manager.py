import hashlib
import json
import os
import subprocess
import sys
import threading


class VenvManager:
    def __init__(self, output_callback, config_manager):
        self.output_callback = output_callback
        self.config_manager = config_manager
        self._lock = threading.Lock()
        self._in_progress = set()

    def ensure_workspace_venv(self, root_path):
        if not root_path:
            return
        root_path = os.path.abspath(root_path)
        with self._lock:
            if root_path in self._in_progress:
                return
            self._in_progress.add(root_path)
        threading.Thread(target=self._ensure_workspace_venv, args=(root_path,), daemon=True).start()

    def _ensure_workspace_venv(self, root_path):
        try:
            cfg = self.config_manager.get("venv") or {}
            auto_create = bool(cfg.get("auto_create", True))
            auto_install = bool(cfg.get("auto_install", True))
            venv_name = cfg.get("path") or ".venv"
            requirements_name = cfg.get("requirements") or "requirements.txt"

            venv_path = os.path.join(root_path, venv_name)

            if auto_create and not os.path.isdir(venv_path):
                self._log(f"[venv] Criando ambiente em {venv_path}...\n")
                if not self._run([sys.executable, "-m", "venv", venv_path], root_path):
                    return

            if not auto_install:
                return

            req_path = os.path.join(root_path, requirements_name)
            if not os.path.isfile(req_path):
                return

            req_hash = _hash_file(req_path)
            state = _load_state(root_path)
            if state.get("requirements_hash") == req_hash:
                return

            venv_python = _venv_python(venv_path)
            if not venv_python or not os.path.exists(venv_python):
                self._log("[venv] Python do .venv nao encontrado.\n")
                return

            self._log(f"[venv] Instalando dependencias de {requirements_name}...\n")
            if self._run([venv_python, "-m", "pip", "install", "-r", req_path], root_path):
                _save_state(root_path, req_hash)
                self._log("[venv] Dependencias instaladas.\n")
        finally:
            with self._lock:
                self._in_progress.discard(root_path)

    def _run(self, args, cwd):
        try:
            process = subprocess.Popen(
                args,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for line in iter(process.stdout.readline, ""):
                if not line:
                    break
                self.output_callback(line)
            process.wait()
            if process.returncode != 0:
                self._log(f"[venv] Falha com codigo {process.returncode}.\n")
                return False
            return True
        except Exception as exc:
            self._log(f"[venv] Erro ao executar: {exc}\n")
            return False

    def _log(self, message):
        try:
            self.output_callback(message)
        except Exception:
            pass


def _hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _state_path(root_path):
    return os.path.join(root_path, ".lcoder", "venv_state.json")


def _load_state(root_path):
    path = _state_path(root_path)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_state(root_path, req_hash):
    path = _state_path(root_path)
    try:
        folder = os.path.dirname(path)
        os.makedirs(folder, exist_ok=True)
        data = {"requirements_hash": req_hash}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _venv_python(venv_path):
    if os.name == "nt":
        return os.path.join(venv_path, "Scripts", "python.exe")
    return os.path.join(venv_path, "bin", "python")
