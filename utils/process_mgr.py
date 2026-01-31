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
            self.output_callback(f"Erro: Configuração para '{language}' não encontrada.\n")
            return

        # Tenta obter o executável configurado ou encontrar no PATH
        executable = config_manager.get("languages", language, "path")
        if not executable or not os.path.exists(executable):
            executable = encontrar_executavel(lang_config["executable"])
            # Fallback final usando shutil.which
            if not os.path.exists(executable):
                executable = shutil.which(lang_config["executable"]) or lang_config["executable"]

        def run():
            try:
                self.output_callback(f"--- Executando {os.path.basename(file_path)} ---\n")
                # Prepara os argumentos substituindo o placeholder {file}
                args = [executable] + [arg.replace("{file}", file_path) for arg in lang_config["run_args"]]
                
                # Executa o processo capturando saída e erro
                process = subprocess.Popen(
                    args, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                stdout, stderr = process.communicate()
                
                if stdout: self.output_callback(stdout)
                if stderr: self.output_callback(stderr)
                
                self.output_callback(f"\n--- Processo finalizado com código {process.returncode} ---\n")
            except Exception as e:
                self.output_callback(f"Erro ao executar processo: {e}\n")

        threading.Thread(target=run, daemon=True).start()

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
            args = [executable]
            if language == "python": args.append("-i")
            elif language == "lua": args.append("-i")
            
            self.terminal_process = subprocess.Popen(
                args, 
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
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
