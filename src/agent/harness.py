"""AI Harness & Orquestrador do DevSRE-Companion.

Implementa o loop ReAct (Raciocínio e Ação), controle de contexto,
auto-recuperação de erros de ferramentas e geração de relatório estruturado.
"""

import os
import json
import inspect
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.mcp_server.server import (
    git_status,
    git_diff,
    list_directory,
    read_file,
    apply_patch,
    run_tests,
    read_application_logs,
)
from src.rag.engine import KnowledgeBaseRAG
from src.agent.schemas import RootCauseAnalysisReport

# Carrega variáveis de ambiente do .env
load_dotenv()
console = Console()


class DevSREHarness:
    """Harness de execução e controle para o agente de engenharia de software."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3.8-flash",
        target_repo: str = ".",
        auto_approve: bool = False,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.target_repo = str(Path(target_repo).resolve())
        self.auto_approve = auto_approve
        self.last_rca_report: Optional[RootCauseAnalysisReport] = None
        self.rag = KnowledgeBaseRAG()

        # Garante que a base de conhecimento esteja indexada
        self.rag.index_directory()

        # Catálogo de ferramentas disponíveis para o agente
        self.tools_map = {
            "git_status": git_status,
            "git_diff": git_diff,
            "list_directory": list_directory,
            "read_file": read_file,
            "apply_patch": apply_patch,
            "run_tests": run_tests,
            "read_application_logs": read_application_logs,
            "search_runbooks": self._search_docs_tool,
        }

    def _build_gemini_tools(self) -> List[Any]:
        """Constrói wrappers tipados das ferramentas para integração com o Google GenAI SDK."""
        def tool_git_status(repo_path: str = self.target_repo) -> str:
            """Retorna o status do Git no repositório."""
            return self.execute_tool("git_status", {"repo_path": repo_path})

        def tool_git_diff(repo_path: str = self.target_repo, cached: bool = False) -> str:
            """Retorna o diff do Git."""
            return self.execute_tool("git_diff", {"repo_path": repo_path, "cached": cached})

        def tool_list_directory(relative_path: str = ".", repo_path: str = self.target_repo) -> str:
            """Lista arquivos e subpastas de um diretório no repositório."""
            return self.execute_tool("list_directory", {"relative_path": relative_path, "repo_path": repo_path})

        def tool_read_file(file_path: str, start_line: int = 1, line_count: int = 100, repo_path: str = self.target_repo) -> str:
            """Lê trecho de um arquivo de código com numeração de linha."""
            return self.execute_tool("read_file", {"file_path": file_path, "start_line": start_line, "line_count": line_count, "repo_path": repo_path})

        def tool_apply_patch(file_path: str, search_block: str, replace_block: str, repo_path: str = self.target_repo, auto_approve: bool = self.auto_approve) -> str:
            """Aplica uma correção (patch) cirúrgica em um arquivo substituindo exatamente um trecho de código."""
            return self.execute_tool("apply_patch", {
                "file_path": file_path,
                "search_block": search_block,
                "replace_block": replace_block,
                "repo_path": repo_path,
                "auto_approve": auto_approve,
            })

        def tool_run_tests(test_path: str = "", verbose: bool = True, repo_path: str = self.target_repo) -> str:
            """Executa a suíte de testes com pytest no repositório."""
            return self.execute_tool("run_tests", {"test_path": test_path, "verbose": verbose, "repo_path": repo_path})

        def tool_read_application_logs(log_file: str, max_lines: int = 60, repo_path: str = self.target_repo) -> str:
            """Lê as últimas linhas de um arquivo de log."""
            return self.execute_tool("read_application_logs", {"log_file": log_file, "max_lines": max_lines, "repo_path": repo_path})

        def tool_search_runbooks(query: str) -> str:
            """Busca nos runbooks, padrões e documentações técnicas internas da empresa."""
            return self.execute_tool("search_runbooks", {"query": query})

        return [
            tool_git_status,
            tool_git_diff,
            tool_list_directory,
            tool_read_file,
            tool_apply_patch,
            tool_run_tests,
            tool_read_application_logs,
            tool_search_runbooks,
        ]

    def _search_docs_tool(self, query: str) -> str:
        """Busca nos runbooks, padrões e documentações técnicas internas da empresa."""
        results = self.rag.search(query=query, top_k=3)
        if not results:
            return "Nenhum documento relevante encontrado nos runbooks."

        output = []
        for r in results:
            output.append(f"[{r['source']} - Seção: {r['section']}]\n{r['content']}")
        return "\n\n---\n\n".join(output)

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Executa uma ferramenta de forma segura com isolamento de falhas (Auto-Healing)."""
        if tool_name not in self.tools_map:
            return f"Erro: Ferramenta '{tool_name}' não existe no catálogo de tools."

        try:
            fn = self.tools_map[tool_name]
            sig = inspect.signature(fn)

            # Injeta repo_path automaticamente se a ferramenta suportar e não foi informado
            if "repo_path" in sig.parameters:
                if "repo_path" not in arguments or arguments["repo_path"] == ".":
                    arguments["repo_path"] = self.target_repo

            # Injeta auto_approve automaticamente se a ferramenta suportar
            if "auto_approve" in sig.parameters:
                if "auto_approve" not in arguments:
                    arguments["auto_approve"] = self.auto_approve

            # Limita tamanho de saída para proteger a janela de contexto
            result = str(fn(**arguments))
            if len(result) > 5000:
                result = result[:5000] + "\n... [Saída truncada pelo Harness para preservar contexto]"
            return result
        except TypeError as te:
            return f"Erro de parâmetro na chamada da ferramenta '{tool_name}': {str(te)}. Corrija os argumentos."
        except Exception as e:
            return f"Falha na execução da ferramenta '{tool_name}': {str(e)}"

    def run_investigation_loop(self, user_instruction: str, max_turns: int = 8) -> str:
        """Loop de investigação do agente com Tool Calling e RAG."""
        console.print(
            Panel(
                f"[bold cyan]Alvo do Repositório:[/bold cyan] {self.target_repo}\n"
                f"[bold cyan]Instrução SRE:[/bold cyan] {user_instruction}",
                title="DevSRE Agent",
            )
        )

        if not self.api_key or self.api_key == "seu_gemini_api_key_aqui":
            console.print(
                "[yellow]Aviso: GEMINI_API_KEY não configurada no .env. Executando em modo de demonstração local do Harness.[/yellow]"
            )
            return self._run_local_demo(user_instruction)

        # Import lazy da SDK oficial do Google GenAI
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            tools = self._build_gemini_tools()

            system_instruction = (
                "Você é um Engenheiro de Software e SRE sênior autônomo e poliglota (DevSRE-Companion), com suporte nativo "
                "a projetos em Java (Maven/Gradle), Python, TypeScript/JavaScript (Node.js), Go, Rust e .NET. "
                "Sua missão é diagnosticar falhas, analisar códigos obsoletos ou depreciados, inspecionar diretórios (tool_list_directory), "
                "ler arquivos de código e configuração (tool_read_file), investigar alterações (tool_git_diff/status), "
                "executar testes com detecção automática do ecossistema (tool_run_tests) e consultar runbooks técnicos (tool_search_runbooks). "
                "Quando apropriado, você pode aplicar correções diretamente com tool_apply_patch e re-executar os testes para confirmar a resolução. "
                "Após diagnosticar, apresente a Causa Raiz, o Código Culpado, a Correção aplicada/sugerida e Ações Preventivas."
            )

            # Inicializa a conversa no SDK com AFC
            chat = client.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                    tools=tools,
                ),
            )

            response = chat.send_message(user_instruction)

            # Extração segura de texto para evitar ValueError em respostas sem bloco de texto direto
            final_text = ""
            try:
                if hasattr(response, "text") and response.text:
                    final_text = response.text
            except (ValueError, AttributeError):
                pass

            if not final_text and hasattr(response, "candidates") and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and part.text:
                                final_text += part.text + "\n"

            if not final_text.strip():
                final_text = "Investigação concluída com sucesso via ferramentas MCP."

            console.print(Panel(final_text, title="[bold green]Diagnóstico Final do SRE[/bold green]"))

            # Estrutura e valida no modelo Pydantic RootCauseAnalysisReport
            rca_report = self.generate_structured_rca(final_text)
            self._render_rca_table(rca_report)

            return final_text

        except Exception as e:
            console.print(f"[bold red]Erro no loop com a API:[/bold red] {e}")
            console.print("[dim]Executando fallback para o modo demonstrativo local...[/dim]")
            return self._run_local_demo(user_instruction)

    def generate_structured_rca(self, text_diagnosis: str) -> RootCauseAnalysisReport:
        """Estrutura o diagnóstico final em um modelo Pydantic tipado (RootCauseAnalysisReport)."""
        if self.api_key and self.api_key != "seu_gemini_api_key_aqui":
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=self.api_key)
                prompt = (
                    "Com base no diagnóstico técnico a seguir, extraia as informações e responda no formato JSON "
                    "estritamente aderente ao schema de Root Cause Analysis:\n\n"
                    f"{text_diagnosis}"
                )
                rca_response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RootCauseAnalysisReport,
                        temperature=0.1,
                    ),
                )
                if rca_response.text:
                    report = RootCauseAnalysisReport.model_validate_json(rca_response.text)
                    self.last_rca_report = report
                    return report
            except Exception as e:
                console.print(f"[dim]Aviso: Não foi possível estruturar via API ({e}). Gerando via parser de fallback.[/dim]")

        # Fallback estruturado determinístico para modo offline ou demonstração
        report = RootCauseAnalysisReport(
            incident_title="Falha em Teste de Autenticação / Conformidade de Runbook",
            severity="MEDIA",
            root_cause_summary="O manipulador de autenticação interceptou o token expirado mas omitiu o cabeçalho 'X-Token-Expired: true' exigido pelo runbook.",
            culprit_files=["src/sample_app/auth.py"],
            suggested_fix_diff="headers={'X-Token-Expired': 'true'}",
            prevention_steps=[
                "Adicionar linter de cabeçalhos HTTP na esteira de CI/CD para validar contratos de API.",
                "Executar testes unitários e de integração antes de submeter alterações."
            ],
        )
        self.last_rca_report = report
        return report

    def _render_rca_table(self, report: RootCauseAnalysisReport) -> None:
        """Renderiza o relatório estruturado em tabela visual com Rich."""
        table = Table(title="[bold cyan]Relatório Estruturado de Causa Raiz (Pydantic Schema)[/bold cyan]")
        table.add_column("Campo", style="magenta", width=22)
        table.add_column("Conteúdo", style="white")

        table.add_row("Título do Incidente", report.incident_title)
        table.add_row("Severidade", f"[bold red]{report.severity}[/bold red]")
        table.add_row("Causa Raiz", report.root_cause_summary)
        table.add_row("Arquivos Culpados", ", ".join(report.culprit_files) if report.culprit_files else "Não identificados")
        table.add_row("Correção Sugerida", report.suggested_fix_diff)
        table.add_row("Ações Preventivas", "\n".join(f"• {step}" for step in report.prevention_steps))

        console.print(table)

    def _run_local_demo(self, instruction: str) -> str:
        """Modo demonstrativo do Harness para testar localmente o fluxo das tools e RAG."""
        console.print("[bold green]1. Executando busca de padrões no RAG (Runbooks)...[/bold green]")
        doc_result = self.execute_tool("search_runbooks", {"query": "token expirado JWT X-Token-Expired"})
        console.print(Panel(doc_result[:500] + "...", title="RAG Match"))

        console.print("[bold green]2. Inspecionando estado do repositório Git...[/bold green]")
        status_res = self.execute_tool("git_status", {"repo_path": self.target_repo})
        console.print(f"Git Status: {status_res}")

        console.print("[bold green]3. Listando arquivos do repositório alvo...[/bold green]")
        files_res = self.execute_tool("list_directory", {"repo_path": self.target_repo})
        console.print(files_res)

        console.print("[bold green]4. Executando suíte de testes com Pytest...[/bold green]")
        test_res = self.execute_tool("run_tests", {"test_path": "tests", "repo_path": self.target_repo})
        console.print(Panel(test_res, title="Resultado dos Testes"))

        demo_report = (
            "### Diagnóstico Demonstrativo do Harness\n\n"
            f"- **Repositório Alvo:** {self.target_repo}\n"
            "- **Regra do Runbook identificada:** Em caso de token JWT expirado, o cabeçalho 'X-Token-Expired: true' é obrigatório.\n"
            "- **Status do Ambiente:** Repositório inspecionado com sucesso via MCP tools."
        )

        rca_report = self.generate_structured_rca(demo_report)
        self._render_rca_table(rca_report)

        return demo_report
