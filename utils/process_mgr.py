import subprocess
import threading
import os
import shutil
from core.languages import LANGUAGES, encontrar_executavel

class ProcessManager:
    def __init__(self, output_callback):
        self.output_callback = output_callback
        self.terminal_process = None

    def run_code(self, language, file_path, config_manager):
        lang_config = LANGUAGES.get(language)
        if not lang_config:
            self.output_callback(f"Erro: Configuracao para '{language}' nao encontrada.\n")
            return

        # Tenta obter o executavel configurado ou encontrar no PATH
        executable = config_manager.get("languages", language, "path")
        if not executable or not os.path.exists(executable):
            executable = encontrar_executavel(lang_config["executable"])
            # Fallback final usando shutil.which
            if not os.path.exists(executable):
                executable = shutil.which(lang_config["executable"]) or lang_config["executable"]
        if language == "python":
            venv_executable = self._resolve_venv_python(file_path, config_manager)
            if venv_executable:
                executable = venv_executable

        def run():
            try:
                self.output_callback(f"--- Executando {os.path.basename(file_path)} ---\n")
                if language == "cpp":
                    base, _ = os.path.splitext(file_path)
                    output_path = f"{base}.exe" if os.name == "nt" else f"{base}.out"
                    compile_args = [executable, file_path, "-o", output_path]

                    compile_proc = subprocess.Popen(
                        compile_args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    )
                    c_stdout, c_stderr = compile_proc.communicate()
                    if c_stdout:
                        self.output_callback(c_stdout)
                    if c_stderr:
                        self.output_callback(c_stderr)

                    if compile_proc.returncode != 0:
                        self.output_callback(f"\n--- Compila????o falhou com codigo {compile_proc.returncode} ---\n")
                        return

                    run_args = [output_path] if os.name == "nt" else ["./" + os.path.basename(output_path)]
                    run_cwd = os.path.dirname(output_path) or None
                    process = subprocess.Popen(
                        run_args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=run_cwd,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    )
                else:
                    # Prepara os argumentos substituindo o placeholder {file}
                    args = [executable] + [arg.replace("{file}", file_path) for arg in lang_config["run_args"]]
                    process = subprocess.Popen(
                        args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    )

                stdout, stderr = process.communicate()

                if stdout:
                    self.output_callback(stdout)
                if stderr:
                    self.output_callback(stderr)

                self.output_callback(f"\n--- Processo finalizado com codigo {process.returncode} ---\n")
            except Exception as e:
                self.output_callback(f"Erro ao executar processo: {e}\n")

        threading.Thread(target=run, daemon=True).start()

    def _resolve_venv_python(self, file_path, config_manager):
        cfg = config_manager.get("venv") or {}
        if not cfg.get("use_for_run", True):
            return None
        venv_name = cfg.get("path") or ".venv"
        root_path = config_manager.get("workspace", "root_path") or ""
        if root_path:
            root_path = os.path.abspath(root_path)
        candidate_paths = []
        if root_path and file_path:
            try:
                file_abs = os.path.abspath(file_path)
                if file_abs.startswith(root_path):
                    candidate_paths.append(os.path.join(root_path, venv_name))
            except Exception:
                pass
        if file_path:
            candidate_paths.append(os.path.join(os.path.dirname(os.path.abspath(file_path)), venv_name))
        for venv_path in candidate_paths:
            venv_python = self._venv_python(venv_path)
            if venv_python and os.path.exists(venv_python):
                return venv_python
        return None

    def _venv_python(self, venv_path):
        if os.name == "nt":
            return os.path.join(venv_path, "Scripts", "python.exe")
        return os.path.join(venv_path, "bin", "python")
    def start_terminal(self, language, config_manager):
        if self.terminal_process:
            self.stop_terminal()

        lang_config = LANGUAGES.get(language)
        executable = config_manager.get("languages", language, "path")
        if not executable or not os.path.exists(executable):
            executable = encontrar_executavel(lang_config["executable"])
            if not os.path.exists(executable):
                executable = shutil.which(lang_config["executable"]) or lang_config["executable"]

        try:
            if os.name == 'nt':
                args = ["cmd.exe"]
            else:
                args = ["/bin/bash"]
            
            self.terminal_process = subprocess.Popen(
                args, 
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                env=os.environ
            )
            
            def listen():
                try:
                    for line in iter(self.terminal_process.stdout.readline, ''):
                        if not line: break
                        self.output_callback(line)
                except:
                    pass
                finally:
                    self.terminal_process = None

            threading.Thread(target=listen, daemon=True).start()
            self.output_callback(f"Terminal {lang_config['name']} iniciado.\n")
        except Exception as e:
            self.output_callback(f"Erro ao iniciar terminal: {e}\n")

    def send_terminal_command(self, command):
        if self.terminal_process and self.terminal_process.stdin:
            try:
                self.terminal_process.stdin.write(command + "\n")
                self.terminal_process.stdin.flush()
            except Exception as e:
                self.output_callback(f"Erro ao enviar comando: {e}\n")
        else:
            self.output_callback("Terminal não está em execução.\n")

    def stop_terminal(self):
        if self.terminal_process:
            try:
                self.terminal_process.terminate()
            except:
                pass
            self.terminal_process = None
            self.output_callback("Terminal parado.\n")
