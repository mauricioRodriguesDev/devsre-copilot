"""Servidor MCP (Model Context Protocol) para DevSRE-Companion.

Expõe ferramentas seguras de inspeção de código, execução de testes
e análise de logs para o agente autônomo.
"""

import os
import sys
import subprocess
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Inicializa o servidor FastMCP
mcp = FastMCP("DevSRE-Tools")


@mcp.tool()
def git_status(repo_path: str = ".") -> str:
    """Retorna o status atual do repositório Git (arquivos modificados, staged e branch)."""
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=repo_path,
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
        cmd = ["git", "diff"]
        if cached:
            cmd.append("--cached")
        result = subprocess.run(
            cmd,
            cwd=repo_path,
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
def run_tests(test_path: str = "", verbose: bool = True) -> str:
    """Executa a suíte de testes com pytest e captura o resultado completo e eventuais tracebacks.

    Args:
        test_path: Caminho opcional para um arquivo ou diretório de teste (ex: 'tests/test_auth.py').
        verbose: Se True, executa com flag -v para detalhes de cada teste.
    """
    try:
        cmd = [sys.executable, "-m", "pytest"]
        if verbose:
            cmd.append("-v")
        if test_path.strip():
            cmd.append(test_path.strip())

        result = subprocess.run(
            cmd,
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
def read_application_logs(log_file: str, max_lines: int = 60) -> str:
    """Lê as últimas linhas de um arquivo de log para diagnosticar erros e stack traces.

    Args:
        log_file: Caminho para o arquivo de log.
        max_lines: Quantidade máxima de linhas finais a serem lidas (padrão: 60).
    """
    try:
        path = Path(log_file)
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
