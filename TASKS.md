# 📋 DevSRE-Companion: Painel de Tarefas e Memória de Execução

Este arquivo serve como **memória persistente** do projeto. Ele registra o progresso das entregas, o roadmap técnico e o status detalhado de cada funcionalidade.

---

## 🚀 Status Geral do Projeto
* **Versão Atual:** `0.1.0` (Pacote `devsre-copilot` instalado em modo editável via `pyproject.toml`)
* **Modelo LLM Ativo:** `gemini-3.8-flash` via Google GenAI SDK (AFC ativado)
* **Precisão de Evals RAG:** `100.0%` (Hit Rate de Fonte @ 2 e Palavras-chave Técnicas)
* **Esteira CI/CD:** GitHub Actions configurado em `.github/workflows/ci.yml`

---

## 📌 Checklist do Roadmap

### Fase 1: Fundação e Arquitetura Base
- [x] Criação da estrutura de pastas modular (`src/`, `knowledge_base/`, `colab_finetuning/`, `tests/`)
- [x] Configuração de ambiente virtual dedicado (Python 3.12 no disco `F:`)
- [x] Configuração de proteção de credenciais (`.gitignore`, `.env.example`, `.env`)
- [x] Inicialização do repositório Git com convenção Conventional Commits

### Fase 2: Servidor MCP e Ferramentas de Código
- [x] Implementação do servidor MCP oficial em `src/mcp_server/server.py` (`FastMCP`)
- [x] Ferramentas de inspeção de repositório (`git_status`, `git_diff`)
- [x] **Motor Poliglota Multi-Linguagem:** Detecção automática de ecossistemas em `run_tests` (Java Maven/Gradle, Node.js, Go, Rust, .NET e Python)
- [x] Filtro de diretórios limpo em `list_directory` (ignora `node_modules`, `target`, `.gradle`, `dist`, `bin`, `obj`)
- [x] Ferramentas de exploração de código (`read_file` com numeração de linhas e limite de 5MB)
- [x] Ferramentas de modificação cirúrgica (`apply_patch` com verificação de unicidade e gate Human-in-the-Loop)
- [x] Testes unitários para todas as ferramentas MCP em `tests/test_tools.py`

### Fase 3: RAG Knowledge Engine & Evals
- [x] Motor de busca vetorial com ChromaDB persistente em `src/rag/engine.py`
- [x] Chunking semântico baseado em cabeçalhos Markdown com preservação de blocos de código
- [x] Runbooks corporativos em `knowledge_base/` (`runbook_auth_jwt.md`, `runbook_database_connection.md`, `runbook_ci_cd_guidelines.md`)
- [x] **Runbook de Modernização Java:** Criado `knowledge_base/runbook_java_modernization.md` (Java 17/21, javax -> jakarta, classes legadas e depreciações)
- [x] Suíte de avaliação quantitativa automatizada em `src/evals/eval_rag.py` com 100% de acerto em 4 cenários chave

### Fase 4: AI Harness, CLI e CI/CD
- [x] Orquestrador ReAct com Auto-Healing e truncagem de contexto em `src/agent/harness.py`
- [x] Esquemas Pydantic tipados para Root Cause Analysis em `src/agent/schemas.py`
- [x] Empacotamento profissional com `pyproject.toml` e comando de console `devsre`
- [x] Pipeline de CI automatizado no GitHub Actions (`.github/workflows/ci.yml`)
- [x] Skill pedagógica interativa `.agent/skills/codebase-to-course/` para onboarding e estudo do portfólio

### Fase 5: Segurança e Hardening (CONCLUÍDA)
- [x] **Fix 1:** Blindagem contra Path Traversal em todas as ferramentas de arquivo (`is_relative_to` e verificação de drives Windows)
- [x] **Fix 2:** Sanitização e mascaramento de segredos/tokens em logs e saídas (`read_application_logs`, incluindo senhas complexas)
- [x] **Fix 3:** Confirmação interativa (Human-in-the-Loop) para operações de escrita (`apply_patch`)
- [x] **Fix 4:** Proteção contra Option/Argument Injection e Path Traversal em `run_tests` (`pytest`)
- [x] **Fix 5:** Chunking Markdown resiliente contra quebra de blocos de código com `#`
- [x] **Fix 6:** Integração ativa do esquema Pydantic `RootCauseAnalysisReport` com exportação `--json`
- [x] **Fix 7:** Salvaguarda de regressão em CI/CD com `devsre eval` (fail-fast exit code 1) e anotação `@pytest.mark.xfail`
- [x] **Testes:** Suíte com 22 testes unitários, RAG e segurança sem filtros artificiais

### Fase 6: Fine-Tuning com LoRA no Google Colab
- [x] Dataset estruturado de treinamento criado em `colab_finetuning/rca_dataset.jsonl` (expandido para 10 cenários reais de SRE)
- [x] Script de fine-tuning com QLoRA/LoRA pronto em `colab_finetuning/fine_tune_lora.py`
- [x] Notebook interativo com visualização de loss e inferência comparativa em `colab_finetuning/devsre_lora_finetuning.ipynb`
- [ ] Execução do treinamento no Google Colab Pro com GPU (T4/L4/A100)
- [ ] Avaliação comparativa de aderência ao formato (Modelo Base vs Modelo Fine-Tuned)

### Fase 7: Publicação e Apresentação de Portfólio
- [x] Atualização final do `README.md` com badges de CI, métricas, guardrails e diagrama arquitetural
- [x] Criação do arquivo de licença de código aberto `LICENSE` (MIT)
- [ ] Conexão e envio para repositório remoto no GitHub (`git push -u origin master`)
