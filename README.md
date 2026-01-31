# 🚀 LCoder: Multi-Language Modular IDE

[![Release](https://img.shields.io/github/v/release/arthurlamonattopro/LCoder?style=flat-square)](https://github.com/arthurlamonattopro/LCoder/releases/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

O **LCoder** é um ambiente de desenvolvimento integrado (IDE) leve, modular e moderno, projetado para oferecer uma experiência fluida em múltiplas linguagens de programação. Refatorado para uma arquitetura modular, o projeto prioriza a facilidade de manutenção, expansão e um visual profissional.

---

## 🎨 Interface e Experiência do Usuário

A interface foi construída utilizando o **CustomTkinter**, proporcionando um visual contemporâneo com suporte nativo a temas e componentes responsivos.

| Funcionalidade | Descrição |
| :--- | :--- |
| **Temas Dinâmicos** | Escolha entre **Dark**, **Light** e **Monokai** para o melhor conforto visual. |
| **Explorador de Arquivos** | Navegação hierárquica por pastas com ícones inteligentes por tipo de arquivo. |
| **Editor Inteligente** | Realce de sintaxe e autocompletar para as principais linguagens do mercado. |
| **Terminal Real** | Integração total com o shell do sistema (CMD/Bash) em tempo real. |

---

## 🏗️ Arquitetura Modular

O projeto foi dividido em componentes lógicos para garantir escalabilidade:

-   📂 `core/`: O "cérebro" da aplicação. Gerencia configurações JSON, definições de linguagens e esquemas de cores.
-   📂 `ui/`: A camada visual. Contém a lógica da janela principal, componentes do editor e o explorador de arquivos.
-   📂 `utils/`: Motores de execução. Responsável pelo gerenciamento de processos externos e integração com o terminal.
-   📄 `main.py`: O ponto de entrada simplificado da aplicação.

---

## 💻 Terminal Integrado de Nova Geração

Diferente de versões anteriores que utilizavam REPLs limitados, o novo terminal do LCoder oferece:

-   ✅ **Acesso Nativo**: Executa comandos diretamente no `cmd.exe` (Windows) ou `bash/zsh` (Linux/macOS).
-   ✅ **Multiplataforma**: Detecção automática do sistema operacional para carregar o shell correto.
-   ✅ **Comunicação Assíncrona**: Utiliza threads separadas para `stdout` e `stderr`, garantindo que a interface nunca trave.
-   ✅ **Suporte a Ferramentas**: Use `git`, `npm`, `pip`, `docker` e qualquer ferramenta de CLI instalada no seu sistema.

---

## 🚀 Como Começar

### Pré-requisitos
-   Python 3.8 ou superior.
-   Dependências principais: `customtkinter`, `Pillow`.

### Instalação e Execução
1.  Clone o repositório ou baixe a [última versão](https://github.com/arthurlamonattopro/LCoder/releases/).
2.  Instale as dependências:
    ```bash
    pip install customtkinter Pillow
    ```
3.  Inicie a IDE:
    ```bash
    python main.py
    ```

---

## 📦 Compilação e Distribuição

O projeto inclui um script de automação (`build.py`) para gerar executáveis nativos usando **PyInstaller**.

### No Windows:
```bash
pip install pyinstaller
python build.py
```
O executável será gerado na pasta `dist/MultiLanguageIDE/`.

### No Linux:
```bash
sudo apt install python3-tk
python3 build.py
```

---

## 🛠️ Suporte a Linguagens
Atualmente, o LCoder oferece suporte nativo (realce e execução) para:
-   🌙 **Lua**
-   🐍 **Python**
-   🟨 **JavaScript (Node.js)**
-   💎 **Ruby**
-   🐘 **PHP**
-   🐪 **Perl**

---

## 🤝 Contribuição

Contribuições são o que tornam a comunidade de código aberto um lugar incrível para aprender, inspirar e criar. Qualquer contribuição que você fizer será **muito apreciada**.

1. Faça um Fork do projeto.
2. Crie sua Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Insira suas alterações e faça o Commit (`git commit -m 'Add AmazingFeature'`).
4. Faça o Push para a Branch (`git push origin feature/AmazingFeature`).
5. Abra um Pull Request.

---

Desenvolvido com ❤️ por [Arthur Lamonatto](https://github.com/arthurlamonattopro).
