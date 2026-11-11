"""Módulo de Avaliação (Evals) para o RAG do DevSRE-Companion.

Permite mensurar de forma automatizada e quantitativa:
- Hit Rate @ K (se o documento correto foi recuperado entre os K primeiros)
- Fidelidade da recuperação em cenários reais de incidentes
"""

from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from src.rag.engine import KnowledgeBaseRAG

console = Console()

# Bateria de testes de avaliação (Ground Truth)
EVAL_DATASET = [
    {
        "query": "Como tratar erro de token JWT expirado e qual cabeçalho HTTP enviar?",
        "expected_source": "runbook_auth_jwt.md",
        "expected_keyword": "X-Token-Expired",
    },
    {
        "query": "O pool de conexões do banco de dados excedeu o limite máximo (QueuePool overflow)",
        "expected_source": "runbook_database_connection.md",
        "expected_keyword": "async with get_db_session()",
    },
    {
        "query": "Qual o padrão exigido para mensagens de commit e formato de relatórios RCA?",
        "expected_source": "runbook_ci_cd_guidelines.md",
        "expected_keyword": "Conventional Commits",
    },
]


def run_rag_evals(top_k: int = 2) -> Dict[str, Any]:
    """Executa a suíte de avaliação do RAG e gera métricas de precisão."""
    rag = KnowledgeBaseRAG()
    rag.index_directory("knowledge_base")

    total_queries = len(EVAL_DATASET)
    hits_source = 0
    hits_keyword = 0

    table = Table(title="[bold cyan]Resultados dos Evals de Recuperação RAG[/bold cyan]")
    table.add_column("Query de Teste", style="magenta", width=35)
    table.add_column("Fonte Esperada", style="green")
    table.add_column("Fonte Obtida (Top 1)", style="yellow")
    table.add_column("Hit Fonte?", justify="center")
    table.add_column("Hit Palavra-Chave?", justify="center")

    for test_case in EVAL_DATASET:
        query = test_case["query"]
        expected_src = test_case["expected_source"]
        expected_kw = test_case["expected_keyword"].lower()

        results = rag.search(query=query, top_k=top_k)
        
        top1_src = results[0]["source"] if results else "NENHUM"
        hit_src = any(r["source"] == expected_src for r in results)
        
        # Checa se o conteúdo recuperado possui a palavra-chave técnica essencial
        combined_text = " ".join([r["content"].lower() for r in results])
        hit_kw = expected_kw in combined_text

        if hit_src:
            hits_source += 1
        if hit_kw:
            hits_keyword += 1

        table.add_row(
            query,
            expected_src,
            top1_src,
            "✅" if hit_src else "❌",
            "✅" if hit_kw else "❌",
        )

    console.print(table)

    metrics = {
        "total_queries": total_queries,
        "source_hit_rate": hits_source / total_queries,
        "keyword_hit_rate": hits_keyword / total_queries,
    }

    console.print(
        f"\n[bold green]Métricas Consolidadas:[/bold green]\n"
        f"- Hit Rate de Fonte @ {top_k}: [bold]{metrics['source_hit_rate'] * 100:.1f}%[/bold]\n"
        f"- Hit Rate de Palavra-chave Técnica: [bold]{metrics['keyword_hit_rate'] * 100:.1f}%[/bold]"
    )

    return metrics


if __name__ == "__main__":
    run_rag_evals()
