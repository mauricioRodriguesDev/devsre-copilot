"""Servidor MCP (Model Context Protocol) para DevSRE-Companion.

Expõe ferramentas seguras de inspeção de código, execução de testes,
leitura de arquivos e aplicação de correções (patches) para o agente autônomo,
com proteção rigorosa contra Path Traversal (CWE-22), mascaramento de segredos (Redaction)
e controle de escrita com Human-in-the-Loop (OWASP LLM06).
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Optional, Tuple
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

    # 5. Mascara pares chave/valor de credenciais comuns (incluindo caracteres especiais)
    text = re.sub(
        r"((?:api[_-]?key|secret|token|password|passwd|auth_token)\s*[:=]\s*['\"]?)([^\s'\",;\r\n]{6,})(['\"]?)",
        r"\1[REDACTED_SECRET]\3",
        text,
        flags=re.IGNORECASE,
    )

    return text


def _resolve_safe_path(file_path: str, repo_path: str = ".") -> Tuple[Optional[Path], Optional[str]]:
    """Valida e resolve com segurança um caminho de arquivo dentro do repositório alvo.

    Protege contra vulnerabilidades de Path Traversal (CWE-22) bloqueando caminhos
    absolutos, letras de unidade do Windows (ex: C:foo), sequências de escape ('../')
    e arquivos/diretórios sensíveis (.env, .git/, chaves privadas).
    """
    try:
        base = Path(repo_path).resolve()
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
        base = Path(repo_path).resolve()
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=str(base),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode != 0:
            return f"Erro ao executar git status: {result.stderr.strip()}"
        output = result.stdout.strip()
        return output if output else "Repositório limpo, nenhuma alteração pendente."
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
        base = Path(repo_path).resolve()
        cmd = ["git", "diff"]
        if cached:
            cmd.append("--cached")
        result = subprocess.run(
            cmd,
            cwd=str(base),
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if result.returncode != 0:
            return f"Erro ao executar git diff: {result.stderr.strip()}"
        output = result.stdout.strip()
        return output if output else "Nenhuma diferença encontrada."
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
            if item.name.startswith(".venv") or item.name == "__pycache__" or item.name == ".git":
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

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"Sucesso: patch aplicado com êxito em {file_path}."
    except Exception as e:
        return f"Erro ao aplicar patch em {file_path}: {str(e)}"


@mcp.tool()
def run_tests(test_path: str = "", verbose: bool = True, repo_path: str = ".") -> str:
    """Executa a suíte de testes com pytest e captura o resultado completo e eventuais tracebacks.

    Protegido contra Argument Injection (flags como -o, -c) e Path Traversal em test_path.

    Args:
        test_path: Caminho opcional para um arquivo ou diretório de teste (ex: 'tests/test_auth.py').
        verbose: Se True, executa com flag -v para detalhes de cada teste.
        repo_path: Diretório onde executar os testes (padrão: '.').
    """
    try:
        base = Path(repo_path).resolve()
        cmd = [sys.executable, "-m", "pytest"]
        if verbose:
            cmd.append("-v")

        clean_test = test_path.strip()
        if clean_test:
            # 1. Proteção contra Argument Injection (ex: -o, -c, --import-mode, etc)
            if clean_test.startswith("-"):
                return f"Segurança: opções e flags de linha de comando não são permitidas em test_path ('{test_path}')."

            # 2. Proteção contra Path Traversal em test_path
            path_obj, err = _resolve_safe_path(clean_test, repo_path)
            if err:
                return err
            if not path_obj.exists():
                return f"Arquivo ou diretório de testes não encontrado: {clean_test}"
            cmd.append(clean_test)

        result = subprocess.run(
            cmd,
            cwd=str(base),
            capture_output=True,
            text=True,
            check=False,
            timeout=45,
        )
        output = result.stdout.strip()
        errors = result.stderr.strip()

        combined = f"--- RESULTADO DOS TESTES (Exit code: {result.returncode}) ---\n"
        if output:
            combined += f"\n[STDOUT]:\n{sanitize_sensitive_data(output)}"
        if errors:
            combined += f"\n[STDERR]:\n{sanitize_sensitive_data(errors)}"
        return combined
    except subprocess.TimeoutExpired:
        return "Tempo limite excedido ao executar os testes (timeout de 45s)."
    except Exception as e:
        return f"Falha ao executar pytest: {str(e)}"


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
