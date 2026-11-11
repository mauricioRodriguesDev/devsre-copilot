"""Ponto de Entrada Principal (CLI) do DevSRE-Companion."""

import sys
import argparse
from rich.console import Console
from rich.panel import Panel

console = Console()


def cmd_investigate(args):
    """Dispara a investigação autônoma do agente."""
    from src.agent.harness import DevSREHarness
    harness = DevSREHarness(target_repo=args.repo)
    query = " ".join(args.query) if args.query else "O teste de autenticação falhou. Investigue a causa e sugira a correção."
    harness.run_investigation_loop(user_instruction=query)


def cmd_mcp_serve(args):
    """Inicia o servidor MCP local para conexão com clientes MCP."""
    console.print(Panel("[bold cyan]Iniciando Servidor MCP DevSRE-Tools via STDIO...[/bold cyan]"))
    from src.mcp_server.server import mcp
    mcp.run()


def cmd_rag_index(args):
    """Reindexa todos os runbooks da base de conhecimento."""
    from src.rag.engine import KnowledgeBaseRAG
    rag = KnowledgeBaseRAG()
    total = rag.index_directory("knowledge_base")
    console.print(f"[bold green]Indexação concluída com sucesso![/bold green] Total de seções indexadas: [bold cyan]{total}[/bold cyan]")


def cmd_eval(args):
    """Executa a bateria de avaliação (Evals) automatizada do RAG."""
    from src.evals.eval_rag import run_rag_evals
    run_rag_evals()


def main():
    parser = argparse.ArgumentParser(
        prog="devsre",
        description="DevSRE-Companion: Autonomous Developer & SRE Copilot"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Comando: investigate
    p_investigate = subparsers.add_parser("investigate", help="Executa o agente em uma tarefa de investigação")
    p_investigate.add_argument("--repo", "-r", default=".", help="Caminho do repositório a ser analisado (padrão: diretório atual)")
    p_investigate.add_argument("query", nargs="*", help="Instrução do desenvolvedor para o agente")
    p_investigate.set_defaults(func=cmd_investigate)

    # Comando: mcp-serve
    p_mcp = subparsers.add_parser("mcp-serve", help="Executa o servidor MCP local via stdio")
    p_mcp.set_defaults(func=cmd_mcp_serve)

    # Comando: rag-index
    p_rag = subparsers.add_parser("rag-index", help="Reindexa os runbooks e documentação")
    p_rag.set_defaults(func=cmd_rag_index)

    # Comando: eval
    p_eval = subparsers.add_parser("eval", help="Roda a suíte de testes de avaliação (Evals)")
    p_eval.set_defaults(func=cmd_eval)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
