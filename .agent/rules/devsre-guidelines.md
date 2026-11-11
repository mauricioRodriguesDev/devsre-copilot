# 📜 DevSRE-Companion: Diretrizes Permanentes de Engenharia e Segurança

Este documento define as regras operacionais, padrões de código e salvaguardas de segurança obrigatórias para o desenvolvimento do DevSRE-Companion. Todas as interações e alterações no projeto devem aderir estritamente a estas diretrizes.

---

## 1. Identidade e Arquitetura do Projeto
* **Nome:** DevSRE-Companion (Copiloto Autônomo de Engenharia de Software e SRE).
* **Linguagem e Runtime:** Python 3.12+ (ambiente virtual em `.venv`).
* **CLI Principal:** `devsre` (definido em `pyproject.toml` apontando para `src.cli:main`).
* **Tecnologias Centrais:**
  * **MCP (Model Context Protocol):** SDK v1 (`mcp<2.0.0`), ferramentas desacopladas em `src/mcp_server/server.py`.
  * **LLM Engine:** Google GenAI SDK (`google-genai`), modelo padrão `gemini-3.8-flash`.
  * **RAG:** ChromaDB persistente (`chroma_db/`), chunking estruturado de Markdown em `src/rag/engine.py`.
  * **AI Harness:** Loop ReAct, tratamento de exceções (Auto-Healing), controle de contexto e schemas Pydantic em `src/agent/`.

---

## 2. Padrões de Git e Ciclo de Vida de Software
* **Conventional Commits Obrigatório:**
  * Todo commit deve seguir o formato: `<tipo>(<escopo>): <descrição em imperativo>`.
  * Tipos permitidos: `feat`, `fix`, `ci`, `docs`, `refactor`, `test`, `chore`.
  * Exemplos: `feat(security): enforce strict path traversal check in mcp tools`, `docs: update TASKS.md`.
* **Commits Atômicos e Granulares:**
  * Nunca criar commits gigantes acumulados. Cada alteração lógica ou correção deve ser commitada de forma independente.
* **Validação Pré-Commit Obrigatória:**
  * Antes de qualquer commit, é obrigatório executar e validar:
    1. `pytest tests/test_tools.py -v` (testes unitários das tools)
    2. `devsre eval` (evals de precisão do RAG)
    3. `git status` (garantir que nenhum arquivo temporário ou segredo esteja staged)

---

## 3. Salvaguardas de Segurança Inegociáveis (Security Guardrails)
1. **Proteção Anti-Path Traversal:**
   * Todas as ferramentas que acessam o sistema de arquivos (`read_file`, `apply_patch`, `list_directory`, `read_application_logs`) DEVEM validar que o caminho resolvido seja rigorosamente filho do repositório alvo (`path.is_relative_to(target_repo)`).
2. **Proteção Absoluta de Segredos:**
   * NUNCA hardcodar nem commitar chaves de API, senhas ou tokens.
   * O arquivo `.env` deve permanecer sempre no `.gitignore`.
   * Segredos capturados em logs devem ser mascarados antes de enviados ao modelo.
3. **Controle de Escrita em Disco (Human-in-the-Loop):**
   * Ferramentas que alteram arquivos em disco (`apply_patch`) devem ter validações cirúrgicas de correspondência única (evitar ambiguidades) e exibir diff claro para o usuário.

---

## 4. Disciplina de Contexto e Memória do Agente
* **Fonte Única da Verdade:** O arquivo `TASKS.md` na raiz do repositório registra o status real das tarefas em andamento. Sempre consultar e atualizar o `TASKS.md` ao iniciar ou concluir um marco.
* **Comunicação:** Respostas técnicas estruturadas, concisas, sem redundância e com links explícitos para os arquivos afetados.
