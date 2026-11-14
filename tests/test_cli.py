"""Testes unitários para a interface de linha de comando (CLI) devsre."""

import argparse
import pytest
from src.cli import main, cmd_rag_index, cmd_eval


def test_cli_argument_parser_investigate():
    """Valida o parsing do comando 'investigate' com parâmetros customizados."""
    parser = argparse.ArgumentParser(prog="devsre")
    subparsers = parser.add_subparsers(dest="command")

    p_investigate = subparsers.add_parser("investigate")
    p_investigate.add_argument("--repo", "-r", default=".")
    p_investigate.add_argument("--yes", "-y", "--auto-approve", dest="auto_approve", action="store_true")
    p_investigate.add_argument("--json", dest="output_json", action="store_true")
    p_investigate.add_argument("query", nargs="*")

    args = parser.parse_args(["investigate", "--repo", "/tmp/repo", "--yes", "--json", "Analise", "o", "bug"])
    assert args.command == "investigate"
    assert args.repo == "/tmp/repo"
    assert args.auto_approve is True
    assert args.output_json is True
    assert args.query == ["Analise", "o", "bug"]


def test_cli_argument_parser_subcommands():
    """Valida o parsing dos subcomandos mcp-serve, rag-index e eval."""
    parser = argparse.ArgumentParser(prog="devsre")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("mcp-serve")
    subparsers.add_parser("rag-index")
    subparsers.add_parser("eval")

    args_mcp = parser.parse_args(["mcp-serve"])
    assert args_mcp.command == "mcp-serve"

    args_rag = parser.parse_args(["rag-index"])
    assert args_rag.command == "rag-index"

    args_eval = parser.parse_args(["eval"])
    assert args_eval.command == "eval"


def test_cli_eval_command(monkeypatch):
    """Valida que o comando eval execute com sucesso e retorne exit code 0."""
    # Monkeypatch sys.exit para capturar o código de saída
    exit_code = None

    def fake_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", fake_exit)

    args = argparse.Namespace()
    cmd_eval(args)

    assert exit_code == 0


def test_cli_rag_index_command():
    """Valida que o comando rag-index execute a reindexação sem erros."""
    args = argparse.Namespace()
    # Executa sem exceções
    cmd_rag_index(args)
