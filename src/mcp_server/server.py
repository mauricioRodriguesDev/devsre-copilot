"""Servidor MCP (Model Context Protocol) para DevSRE-Companion.

Expõe ferramentas seguras de inspeção de código, execução de testes,
leitura de arquivos e aplicação de correções (patches) para o agente autônomo,
com proteção rigorosa contra Path Traversal (CWE-22).
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from mcp.server.fastmcp import FastMCP

# Inicializa o servidor FastMCP
mcp = FastMCP("DevSRE-Tools")


def _resolve_safe_path(file_path: str, repo_path: str = ".") -> Tuple[Optional[Path], Optional[str]]:
    """Valida e resolve com segurança um caminho de arquivo dentro do repositório alvo.

    Protege contra vulnerabilidades de Path Traversal (CWE-22) bloqueando caminhos
    absolutos e sequências de escape ('../') que tentem sair da raiz do projeto.
    """
    try:
        base = Path(repo_path).resolve()
        clean = Path(file_path)

        # 1. Rejeita caminhos absolutos (ex: C:/Windows/..., /etc/passwd)
        if clean.is_absolute():
            return None, f"Segurança: caminhos absolutos não são permitidos ('{file_path}'). Use um caminho relativo ao repositório."

        target = (base / clean).resolve()

        # 2. Garante que o caminho resolvido seja estritamente filho do repositório
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

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, start_idx + line_count)

        selected_lines = lines[start_idx:end_idx]
        output = [f"--- Arquivo: {file_path} (Linhas {start_idx + 1} a {end_idx} de {total_lines}) ---"]

        for idx, line in enumerate(selected_lines, start=start_idx + 1):
            output.append(f"{idx:4d} | {line.rstrip()}")

        return "\n".join(output)
    except Exception as e:
        return f"Erro ao ler arquivo {file_path}: {str(e)}"


@mcp.tool()
def apply_patch(file_path: str, search_block: str, replace_block: str, repo_path: str = ".") -> str:
    """Aplica uma correção (patch) cirúrgica em um arquivo substituindo exatamente um trecho de código.

    Args:
        file_path: Caminho relativo do arquivo a ser modificado.
        search_block: Trecho exato de código a ser substituído.
        replace_block: Novo código que entrará no lugar.
        repo_path: Caminho raiz do repositório.
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

        new_content = content.replace(search_block, replace_block, 1)

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"Sucesso: patch aplicado com êxito em {file_path}."
    except Exception as e:
        return f"Erro ao aplicar patch em {file_path}: {str(e)}"


@mcp.tool()
def run_tests(test_path: str = "", verbose: bool = True, repo_path: str = ".") -> str:
    """Executa a suíte de testes com pytest e captura o resultado completo e eventuais tracebacks.

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
        if test_path.strip():
            cmd.append(test_path.strip())

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
            combined += f"\n[STDOUT]:\n{output}"
        if errors:
            combined += f"\n[STDERR]:\n{errors}"
        return combined
    except subprocess.TimeoutExpired:
        return "Tempo limite excedido ao executar os testes (timeout de 45s)."
    except Exception as e:
        return f"Falha ao executar pytest: {str(e)}"


@mcp.tool()
def read_application_logs(log_file: str, max_lines: int = 60, repo_path: str = ".") -> str:
    """Lê as últimas linhas de um arquivo de log para diagnosticar erros e stack traces.

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
        return "".join(tail_lines) if tail_lines else "Arquivo de log vazio."
    except Exception as e:
        return f"Erro ao ler arquivo de log: {str(e)}"


if __name__ == "__main__":
    # Quando executado diretamente, inicia o servidor MCP via stdio
    mcp.run()
