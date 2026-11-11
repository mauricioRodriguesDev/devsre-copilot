"""AI Harness & Orquestrador do DevSRE-Companion.

Implementa o loop ReAct (Raciocínio e Ação), controle de contexto,
auto-recuperação de erros de ferramentas e geração de relatório estruturado.
"""

import os
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.mcp_server.server import (
    git_status,
    git_diff,
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

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.rag = KnowledgeBaseRAG()
        
        # Garante que a base de conhecimento esteja indexada
        self.rag.index_directory("knowledge_base")

        # Catálogo de ferramentas disponíveis para o agente
        self.tools_map = {
            "git_status": git_status,
            "git_diff": git_diff,
            "run_tests": run_tests,
            "read_application_logs": read_application_logs,
            "search_runbooks": self._search_docs_tool,
        }

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
            # Limita tamanho de saída para proteger a janela de contexto
            result = str(fn(**arguments))
            if len(result) > 4000:
                result = result[:4000] + "\n... [Saída truncada pelo Harness para preservar contexto]"
            return result
        except TypeError as te:
            return f"Erro de parâmetro na chamada da ferramenta '{tool_name}': {str(te)}. Corrija os argumentos."
        except Exception as e:
            return f"Falha na execução da ferramenta '{tool_name}': {str(e)}"

    def run_investigation_loop(self, user_instruction: str, max_turns: int = 6) -> str:
        """Loop de investigação do agente com Tool Calling e RAG."""
        console.print(Panel(f"[bold cyan]Nova Investigação SRE:[/bold cyan] {user_instruction}", title="DevSRE Agent"))

        if not self.api_key or self.api_key == "seu_gemini_api_key_aqui":
            console.print("[yellow]Aviso: GEMINI_API_KEY não configurada no .env. Executando em modo de demonstração local do Harness.[/yellow]")
            return self._run_local_demo(user_instruction)

        # Import lazy da SDK oficial do Google GenAI
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Lista de funções que o modelo pode invocar
            tools = [
                git_status,
                git_diff,
                run_tests,
                read_application_logs,
                self._search_docs_tool,
            ]

            system_instruction = (
                "Você é um Engenheiro de Software e SRE sênior autônomo (DevSRE-Companion). "
                "Sua missão é diagnosticar falhas de testes, investigar alterações de código (git diff/status), "
                "analisar logs e SEMPRE consultar os runbooks internos com search_runbooks para garantir "
                "que as correções sigam estritamente os padrões da empresa. "
                "Após diagnosticar, apresente a Causa Raiz, o Código Culpado, a Correção sugerida e Ações Preventivas."
            )

            # Inicializa a conversa no SDK
            chat = client.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                    tools=tools,
                )
            )

            response = chat.send_message(user_instruction)
            turns = 0

            while turns < max_turns:
                turns += 1

                # Verifica se o modelo solicitou chamadas de ferramentas
                function_calls = getattr(response, "function_calls", None)
                if not function_calls:
                    # Nenhuma tool call pendente: resposta final atingida
                    break

                for call in function_calls:
                    tool_name = call.name
                    args = dict(call.args) if call.args else {}
                    console.print(f"[bold magenta]⚙️ Tool Call solicitada:[/bold magenta] [green]{tool_name}[/green]({args})")

                    # Executa a tool no harness
                    tool_result = self.execute_tool(tool_name, args)

                    # Devolve o resultado da tool para o modelo continuar raciocinando
                    response = chat.send_message(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={"result": tool_result}
                        )
                    )

            final_text = response.text if hasattr(response, "text") and response.text else "Investigação concluída."
            console.print(Panel(final_text, title="[bold green]Diagnóstico Final do SRE[/bold green]"))
            return final_text

        except Exception as e:
            console.print(f"[bold red]Erro no loop com a API:[/bold red] {e}")
            console.print("[dim]Executando fallback para o modo demonstrativo local...[/dim]")
            return self._run_local_demo(user_instruction)

    def _run_local_demo(self, instruction: str) -> str:
        """Modo demonstrativo do Harness para testar localmente o fluxo das tools e RAG."""
        console.print("[bold green]1. Executando busca de padrões no RAG (Runbooks)...[/bold green]")
        doc_result = self.execute_tool("search_runbooks", {"query": "token expirado JWT X-Token-Expired"})
        console.print(Panel(doc_result[:500] + "...", title="RAG Match"))

        console.print("[bold green]2. Inspecionando estado do repositório Git...[/bold green]")
        status_res = self.execute_tool("git_status", {})
        console.print(f"Git Status: {status_res}")

        console.print("[bold green]3. Executando suíte de testes com Pytest...[/bold green]")
        test_res = self.execute_tool("run_tests", {"test_path": "tests"})
        console.print(Panel(test_res, title="Resultado dos Testes"))

        demo_report = (
            "### Diagnóstico Demonstrativo do Harness\n\n"
            "- **Regra do Runbook identificada:** Em caso de token JWT expirado, o cabeçalho 'X-Token-Expired: true' é obrigatório.\n"
            "- **Status do Ambiente:** Repositório inspecionado com sucesso via MCP tools.\n"
            "- **Próximo Passo:** Configurar a sua GEMINI_API_KEY no arquivo .env para que o agente execute o loop de raciocínio dinâmico com o modelo."
        )
        return demo_report
