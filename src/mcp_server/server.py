"""Servidor MCP (Model Context Protocol) para DevSRE-Companion.

Expõe ferramentas seguras de inspeção de código, execução de testes,
leitura de arquivos e aplicação de correções (patches) para o agente autônomo,
com proteção rigorosa contra Path Traversal (CWE-22), mascaramento de segredos (Redaction)
e controle de escrita com Human-in-the-Loop (OWASP LLM06).
"""

import os
import re
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List
from mcp.server.fastmcp import FastMCP

# Inicializa o servidor FastMCP
mcp = FastMCP("DevSRE-Tools")


# Conjuntos de arquivos, extensões e diretórios restritos para prevenir vazamentos e adulterações
BLOCKED_SENSITIVE_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    ".env.test",
    "credentials.json",
    "service_account.json",
    "id_rsa",
    "id_ed25519",
}

BLOCKED_SENSITIVE_EXTENSIONS = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}

BLOCKED_SENSITIVE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    ".vscode",
    ".idea",
}

# Pastas de build/dependências comuns ignoradas na listagem de diretórios para não sobrecarregar contexto
IGNORED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    ".next",
    ".nuxt",
    "dist",
    "build",
    "target",
    ".gradle",
    "bin",
    "obj",
    "vendor",
}

# Configurações de timeouts com defaults seguros e suporte a variáveis de ambiente
DEFAULT_GIT_STATUS_TIMEOUT = int(os.getenv("DEVSRE_GIT_STATUS_TIMEOUT", "10"))
DEFAULT_GIT_DIFF_TIMEOUT = int(os.getenv("DEVSRE_GIT_DIFF_TIMEOUT", "15"))
DEFAULT_TEST_TIMEOUT = int(os.getenv("DEVSRE_TEST_TIMEOUT", "60"))


def sanitize_sensitive_data(text: str) -> str:
    """Mascara credenciais sensíveis (chaves de API, senhas de banco, tokens JWT e Bearer).

    Evita que segredos capturados em logs ou saídas de testes vazem para o prompt
    da LLM ou fiquem armazenados em texto puro na sessão.
    """
    if not text:
        return text

    # 1. Mascara chaves de API da Google (AIza... e novas chaves de projeto AQ...)
    text = re.sub(
        r"(?:AIza[0-9A-Za-z\-_]{30,}|AQ\.[A-Za-z0-9\-_]{20,})",
        "[REDACTED_GOOGLE_KEY]",
        text,
    )

    # 2. Mascara tokens JWT completos (header.payload.signature)
    text = re.sub(
        r"eyJ[A-Za-z0-9\-_=]+\.eyJ[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_.+/=]+",
        "[REDACTED_JWT_TOKEN]",
        text,
    )

    # 3. Mascara tokens de cabeçalho Bearer
    text = re.sub(
        r"(Bearer\s+)[A-Za-z0-9\-_.~+/=]{16,}",
        r"\1[REDACTED_BEARER_TOKEN]",
        text,
        flags=re.IGNORECASE,
    )

    # 4. Mascara senhas em URIs de conexão de banco de dados
    text = re.sub(
        r"((?:postgresql|postgres|mysql|mariadb|mongodb|redis|amqp)://[^:\s/]+:)([^@\s]+)(@)",
        r"\1[REDACTED_PASSWORD]\3",
        text,
        flags=re.IGNORECASE,
    )

    # 5. Mascara credenciais da AWS (Access Key ID e Secret Key)
    text = re.sub(
        r"\b(?:A3T[A-Z0-9]|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16})\b",
        "[REDACTED_AWS_KEY]",
        text,
    )

    # 6. Mascara tokens de acesso pessoal do GitHub (ghp, gho, ghu, ghs, ghr)
    text = re.sub(
        r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b",
        "[REDACTED_GITHUB_TOKEN]",
        text,
    )

    # 7. Mascara chaves de API Stripe (sk_live, sk_test, rk_live, rk_test)
    text = re.sub(
        r"\b(?:sk|rk)_(?:live|test)_[0-9a-zA-Z]{24,}\b",
        "[REDACTED_STRIPE_KEY]",
        text,
    )

    # 8. Mascara pares chave/valor de credenciais comuns (ignorando se já foi redigido)
    text = re.sub(
        r"((?:api[_-]?key|secret|token|password|passwd|auth_token)\s*[:=]\s*['\"]?)(?!\[REDACTED_)([^\s'\",;\r\n]{6,})(['\"]?)",
        r"\1[REDACTED_SECRET]\3",
        text,
        flags=re.IGNORECASE,
    )

    return text


def _resolve_safe_repo_dir(repo_path: str = ".") -> Tuple[Optional[Path], Optional[str]]:
    """Valida se o diretório do repositório é seguro para inspeção e execução de comandos.

    Bloqueia diretórios inexistentes, raízes de sistema de arquivos e pastas sensíveis protegidas.
    """
    try:
        base = Path(repo_path).resolve()

        if not base.exists():
            return None, f"Diretório do repositório não encontrado: {repo_path}"
        if not base.is_dir():
            return None, f"O caminho do repositório não aponta para um diretório: {repo_path}"

        # 1. Rejeita raízes absolutas do sistema de arquivos (ex: C:\, \, /)
        if base == Path(base.anchor) or str(base) == base.drive + "\\":
            return None, f"Segurança: não é permitido executar operações na raiz do sistema ('{repo_path}')."

        # 2. Rejeita pastas sensíveis protegidas
        if base.name.lower() in BLOCKED_SENSITIVE_DIRS:
            return None, f"Segurança: acesso ao diretório protegido/sensível '{base.name}' não é permitido."

        return base, None
    except Exception as e:
        return None, f"Erro ao validar diretório do repositório: {str(e)}"


def _resolve_safe_path(file_path: str, repo_path: str = ".") -> Tuple[Optional[Path], Optional[str]]:
    """Valida e resolve com segurança um caminho de arquivo dentro do repositório alvo.

    Protege contra vulnerabilidades de Path Traversal (CWE-22) bloqueando caminhos
    absolutos, letras de unidade do Windows (ex: C:foo), sequências de escape ('../')
    e arquivos/diretórios sensíveis (.env, .git/, chaves privadas).
    """
    try:
        base, err = _resolve_safe_repo_dir(repo_path)
        if err:
            return None, err
        clean = Path(file_path)

        # 1. Rejeita caminhos absolutos ou com unidade de disco (ex: C:/Windows/..., C:foo, /etc/passwd)
        if clean.is_absolute() or bool(clean.drive):
            return None, f"Segurança: caminhos absolutos ou com unidade não são permitidos ('{file_path}'). Use um caminho relativo ao repositório."

        # 2. Bloqueia acesso a arquivos ou extensões sensíveis (.env, .pem, .key, credentials.json)
        file_name = clean.name.lower()
        if file_name in BLOCKED_SENSITIVE_FILES or clean.suffix.lower() in BLOCKED_SENSITIVE_EXTENSIONS:
            return None, f"Segurança: acesso a arquivos ou diretórios protegidos/sensíveis não é permitido ('{file_path}')."

        # 3. Bloqueia acesso a pastas protegidas (.git, .venv, .vscode, .idea)
        for part in clean.parts:
            if part.lower() in BLOCKED_SENSITIVE_DIRS:
                return None, f"Segurança: acesso a arquivos ou diretórios protegidos/sensíveis não é permitido ('{file_path}')."

        target = (base / clean).resolve()

        # 4. Garante que o caminho resolvido seja estritamente filho do repositório
        if not target.is_relative_to(base):
            return None, f"Segurança: tentativa de Path Traversal detectada. O caminho '{file_path}' tenta acessar arquivos fora do repositório alvo."

        return target, None
    except Exception as e:
        return None, f"Erro ao validar caminho de arquivo: {str(e)}"


@mcp.tool()
def git_status(repo_path: str = ".") -> str:
    """Retorna o status atual do repositório Git (arquivos modificados, staged e branch)."""
    try:
        base, err = _resolve_safe_repo_dir(repo_path)
        if err:
            return err
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=str(base),
            capture_output=True,
            text=True,
            check=False,
            timeout=DEFAULT_GIT_STATUS_TIMEOUT,
        )
        if result.returncode != 0:
            return f"Erro ao executar git status: {result.stderr.strip()}"
        output = result.stdout.strip()
        return output if output else "Repositório limpo, nenhuma alteração pendente."
    except subprocess.TimeoutExpired:
        return f"Tempo limite excedido ao executar git status (timeout de {DEFAULT_GIT_STATUS_TIMEOUT}s)."
    except Exception as e:
        return f"Falha ao executar git status: {str(e)}"


@mcp.tool()
def git_diff(repo_path: str = ".", cached: bool = False) -> str:
    """Retorna a diferença (diff) unificada das alterações recentes no código.

    Args:
        repo_path: Diretório do repositório Git.
        cached: Se True, mostra o diff dos arquivos em stage (git diff --cached).
    """
    try:
        base, err = _resolve_safe_repo_dir(repo_path)
        if err:
            return err
        cmd = ["git", "diff"]
        if cached:
            cmd.append("--cached")
        result = subprocess.run(
            cmd,
            cwd=str(base),
            capture_output=True,
            text=True,
            check=False,
            timeout=DEFAULT_GIT_DIFF_TIMEOUT,
        )
        if result.returncode != 0:
            return f"Erro ao executar git diff: {result.stderr.strip()}"
        output = result.stdout.strip()
        return output if output else "Nenhuma diferença encontrada."
    except subprocess.TimeoutExpired:
        return f"Tempo limite excedido ao executar git diff (timeout de {DEFAULT_GIT_DIFF_TIMEOUT}s)."
    except Exception as e:
        return f"Falha ao executar git diff: {str(e)}"


@mcp.tool()
def list_directory(relative_path: str = ".", repo_path: str = ".") -> str:
    """Lista arquivos e subpastas de um diretório no repositório alvo.

    Args:
        relative_path: Caminho relativo dentro do repositório (padrão: raiz).
        repo_path: Caminho raiz do repositório.
    """
    try:
        target, err = _resolve_safe_path(relative_path, repo_path)
        if err:
            return err

        if not target.exists():
            return f"Diretório não encontrado: {relative_path}"
        if not target.is_dir():
            return f"O caminho especificado não é um diretório: {relative_path}"

        entries = []
        for item in sorted(target.iterdir()):
            if item.name in IGNORED_DIR_NAMES or item.name.startswith(".venv"):
                continue
            suffix = "/" if item.is_dir() else ""
            entries.append(f"{item.name}{suffix}")

        return "\n".join(entries) if entries else "Diretório vazio."
    except Exception as e:
        return f"Erro ao listar diretório: {str(e)}"


@mcp.tool()
def read_file(file_path: str, start_line: int = 1, line_count: int = 100, repo_path: str = ".") -> str:
    """Lê um trecho de um arquivo de código com numeração de linhas.

    Args:
        file_path: Caminho relativo do arquivo no repositório.
        start_line: Linha inicial a ser lida (1-indexada).
        line_count: Quantidade de linhas a ler (padrão: 100).
        repo_path: Caminho raiz do repositório.
    """
    try:
        path, err = _resolve_safe_path(file_path, repo_path)
        if err:
            return err

        if not path.exists():
            return f"Arquivo não encontrado: {file_path}"
        if path.is_dir():
            return f"O caminho aponta para um diretório, não um arquivo: {file_path}"

        # Salvaguarda contra estouro de memória: rejeita arquivos maiores que 5MB
        if path.stat().st_size > 5 * 1024 * 1024:
            return f"Segurança: arquivo excede o limite máximo permitido de 5MB para inspeção: {file_path}"

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, start_idx + line_count)

        selected_lines = lines[start_idx:end_idx]
        output = [f"--- Arquivo: {file_path} (Linhas {start_idx + 1} a {end_idx} de {total_lines}) ---"]

        for idx, line in enumerate(selected_lines, start=start_idx + 1):
            output.append(f"{idx:4d} | {line.rstrip()}")

        raw_result = "\n".join(output)
        return sanitize_sensitive_data(raw_result)
    except Exception as e:
        return f"Erro ao ler arquivo {file_path}: {str(e)}"


@mcp.tool()
def apply_patch(
    file_path: str,
    search_block: str,
    replace_block: str,
    repo_path: str = ".",
    auto_approve: bool = False,
) -> str:
    """Aplica uma correção (patch) cirúrgica em um arquivo substituindo exatamente um trecho de código.

    Possui proteção Human-in-the-Loop: solicita confirmação interativa antes de alterar o disco,
    a menos que auto_approve=True seja explicitado.

    Args:
        file_path: Caminho relativo do arquivo a ser modificado.
        search_block: Trecho exato de código a ser substituído.
        replace_block: Novo código que entrará no lugar.
        repo_path: Caminho raiz do repositório.
        auto_approve: Se True, aplica a alteração sem solicitar confirmação manual.
    """
    try:
        path, err = _resolve_safe_path(file_path, repo_path)
        if err:
            return err

        if not path.exists():
            return f"Arquivo não encontrado: {file_path}"

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if search_block not in content:
            return (
                f"Erro de correspondência: o bloco de código a ser substituído não foi encontrado exatamente como especificado em {file_path}. "
                "Use read_file para confirmar a formatação e indentação exata antes de aplicar o patch."
            )

        occurrences = content.count(search_block)
        if occurrences > 1:
            return (
                f"Ambiguidade: o bloco a ser substituído aparece {occurrences} vezes no arquivo. "
                "Forneça mais linhas de contexto ao redor para tornar a substituição unívoca."
            )

        # Gate Human-in-the-Loop de Confirmação Prévia
        if not auto_approve:
            diff_preview = (
                f"\n--- [PROPOSTA DE PATCH EM: {file_path}] ---\n"
                f"[-] REMOVER:\n{search_block}\n\n"
                f"[+] INSERIR:\n{replace_block}\n"
                f"--------------------------------------------"
            )
            print(diff_preview)

            if sys.stdin and sys.stdin.isatty():
                try:
                    choice = input(f"Confirmar aplicação do patch em '{file_path}'? [s/N]: ").strip().lower()
                    if choice not in ("s", "sim", "y", "yes"):
                        return f"Operação cancelada pelo desenvolvedor: o patch em '{file_path}' não foi aplicado."
                except (EOFError, KeyboardInterrupt):
                    return f"Operação abortada: confirmação interrompida para '{file_path}'."
            else:
                return (
                    f"Proteção de Segurança: execução em ambiente não-interativo requer flag auto_approve=True "
                    f"para autorizar gravação em disco no arquivo '{file_path}'."
                )

        new_content = content.replace(search_block, replace_block, 1)

        # Escrita atômica via arquivo temporário seguro para evitar corrupção em caso de falha de I/O
        temp_file = path.with_name(f".{path.name}.tmp_patch")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            temp_file.replace(path)
        except Exception:
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
            raise

        return f"Sucesso: patch aplicado com êxito em {file_path}."
    except Exception as e:
        return f"Erro ao aplicar patch em {file_path}: {str(e)}"


def detect_project_ecosystem(
    repo_path: Path, clean_test: str = "", verbose: bool = True
) -> Tuple[str, Optional[List[str]], Optional[str]]:
    """Detecta automaticamente o ecossistema do projeto (Java Maven/Gradle, Node.js, Go, Rust, .NET, Python).

    Retorna:
        (nome_do_ecossistema, comando_em_lista, mensagem_de_erro_se_houver)
    """
    is_windows = sys.platform == "win32"

    # 1. Java / Kotlin (Apache Maven)
    if (repo_path / "pom.xml").exists():
        wrapper = repo_path / ("mvnw.cmd" if is_windows else "mvnw")
        mvn_bin = str(wrapper) if wrapper.exists() else shutil.which("mvn")
        if not mvn_bin:
            return (
                "Maven (Java)",
                None,
                "Ecossistema detectado: Maven (Java), mas o executável 'mvn' ou wrapper 'mvnw' "
                "não foi encontrado no PATH. Instale o Apache Maven ou adicione o wrapper mvnw no repositório.",
            )
        cmd = [mvn_bin, "test"]
        if clean_test:
            cmd.append(f"-Dtest={clean_test}")
        return "Maven (Java)", cmd, None

    # 2. Java / Kotlin (Gradle)
    if (repo_path / "build.gradle").exists() or (repo_path / "build.gradle.kts").exists():
        wrapper = repo_path / ("gradlew.bat" if is_windows else "gradlew")
        gradle_bin = str(wrapper) if wrapper.exists() else shutil.which("gradle")
        if not gradle_bin:
            return (
                "Gradle (Java/Kotlin)",
                None,
                "Ecossistema detectado: Gradle (Java/Kotlin), mas o executável 'gradle' ou wrapper 'gradlew' "
                "não foi encontrado no PATH. Instale o Gradle ou adicione o wrapper gradlew no repositório.",
            )
        cmd = [gradle_bin, "test"]
        if clean_test:
            cmd.extend(["--tests", clean_test])
        return "Gradle (Java/Kotlin)", cmd, None

    # 3. JavaScript / TypeScript (Node.js)
    if (repo_path / "package.json").exists():
        pm = "npm"
        if (repo_path / "pnpm-lock.yaml").exists() and shutil.which("pnpm"):
            pm = "pnpm"
        elif (repo_path / "yarn.lock").exists() and shutil.which("yarn"):
            pm = "yarn"
        elif (repo_path / "bun.lockb").exists() and shutil.which("bun"):
            pm = "bun"

        pm_bin = shutil.which(pm)
        if not pm_bin:
            return (
                "Node.js",
                None,
                f"Ecossistema detectado: Node.js, mas o gerenciador '{pm}' não foi encontrado no PATH.",
            )
        cmd = [pm_bin, "test"]
        if clean_test:
            cmd.extend(["--", clean_test])
        return f"Node.js ({pm})", cmd, None

    # 4. Go
    if (repo_path / "go.mod").exists():
        go_bin = shutil.which("go")
        if not go_bin:
            return "Go", None, "Ecossistema detectado: Go, mas o executável 'go' não foi encontrado no PATH."
        cmd = [go_bin, "test"]
        if verbose:
            cmd.append("-v")
        cmd.append(f"./{clean_test}/..." if clean_test else "./...")
        return "Go", cmd, None

    # 5. Rust (Cargo)
    if (repo_path / "Cargo.toml").exists():
        cargo_bin = shutil.which("cargo")
        if not cargo_bin:
            return "Rust (Cargo)", None, "Ecossistema detectado: Rust (Cargo), mas o executável 'cargo' não foi encontrado no PATH."
        cmd = [cargo_bin, "test"]
        if clean_test:
            cmd.append(clean_test)
        return "Rust (Cargo)", cmd, None

    # 6. .NET / C#
    if list(repo_path.glob("*.sln")) or list(repo_path.glob("*.csproj")):
        dotnet_bin = shutil.which("dotnet")
        if not dotnet_bin:
            return ".NET", None, "Ecossistema detectado: .NET, mas o executável 'dotnet' não foi encontrado no PATH."
        cmd = [dotnet_bin, "test"]
        if clean_test:
            cmd.extend(["--filter", clean_test])
        return ".NET", cmd, None

    # 7. Python (Padrão)
    cmd = [sys.executable, "-m", "pytest"]
    if verbose:
        cmd.append("-v")
    if clean_test:
        cmd.append(clean_test)
    return "Python (pytest)", cmd, None


@mcp.tool()
def run_tests(test_path: str = "", verbose: bool = True, repo_path: str = ".") -> str:
    """Executa a suíte de testes com detecção automática de ecossistema (Java Maven/Gradle, Node.js, Go, Rust, .NET, Python).

    Protegido contra Argument Injection (flags como -o, -c) e Path Traversal em test_path e repo_path.

    Args:
        test_path: Caminho ou filtro opcional de teste (ex: 'tests/test_auth.py', 'com.empresa.service.AuthTest').
        verbose: Se True, executa com flag de verbosidade onde aplicável.
        repo_path: Diretório onde executar os testes (padrão: '.').
    """
    try:
        base, err = _resolve_safe_repo_dir(repo_path)
        if err:
            return err

        clean_test = test_path.strip()
        if clean_test:
            # 1. Proteção contra Argument Injection (ex: -o, -c, --import-mode, etc)
            if clean_test.startswith("-"):
                return f"Segurança: opções e flags de linha de comando não são permitidas em test_path ('{test_path}')."

            # 2. Se for um arquivo existente com caminho relativo, valida se não é traversal
            if ("/" in clean_test or "\\" in clean_test) or (base / clean_test).exists():
                path_obj, err = _resolve_safe_path(clean_test, repo_path)
                if err:
                    return err
                if not path_obj.exists():
                    return f"Arquivo ou diretório de testes não encontrado: {clean_test}"

        # 3. Detecta ecossistema e monta o comando de testes apropriado
        ecosystem_name, cmd, err = detect_project_ecosystem(base, clean_test, verbose)
        if err:
            return f"[{ecosystem_name}] {err}"

        result = subprocess.run(
            cmd,
            cwd=str(base),
            capture_output=True,
            text=True,
            check=False,
            timeout=DEFAULT_TEST_TIMEOUT,
        )
        output = result.stdout.strip()
        errors = result.stderr.strip()

        combined = f"--- RESULTADO DOS TESTES [{ecosystem_name}] (Exit code: {result.returncode}) ---\n"
        if output:
            combined += f"\n[STDOUT]:\n{sanitize_sensitive_data(output)}"
        if errors:
            combined += f"\n[STDERR]:\n{sanitize_sensitive_data(errors)}"
        return combined
    except subprocess.TimeoutExpired:
        return f"Tempo limite excedido ao executar os testes (timeout de {DEFAULT_TEST_TIMEOUT}s)."
    except Exception as e:
        return f"Falha ao executar suíte de testes: {str(e)}"


@mcp.tool()
def read_application_logs(log_file: str, max_lines: int = 60, repo_path: str = ".") -> str:
    """Lê as últimas linhas de um arquivo de log para diagnosticar erros e stack traces,
    aplicando sanitização e mascaramento automático de credenciais sensíveis.

    Args:
        log_file: Caminho para o arquivo de log.
        max_lines: Quantidade máxima de linhas finais a serem lidas (padrão: 60).
        repo_path: Diretório raiz do repositório.
    """
    try:
        path, err = _resolve_safe_path(log_file, repo_path)
        if err:
            return err

        if not path.exists():
            return f"Arquivo de log não encontrado: {log_file}"

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        tail_lines = lines[-max_lines:]
        raw_output = "".join(tail_lines) if tail_lines else "Arquivo de log vazio."
        return sanitize_sensitive_data(raw_output)
    except Exception as e:
        return f"Erro ao ler arquivo de log: {str(e)}"


if __name__ == "__main__":
    # Quando executado diretamente, inicia o servidor MCP via stdio
    mcp.run()
