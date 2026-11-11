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
- [x] Ferramentas de execução de testes (`run_tests` com suporte a `repo_path`)
- [x] Ferramentas de exploração de código (`list_directory`, `read_file` com linhas)
- [x] Ferramentas de modificação cirúrgica (`apply_patch` com verificação de unicidade)
- [x] Testes unitários para todas as ferramentas MCP em `tests/test_tools.py`

### Fase 3: RAG Knowledge Engine & Evals
- [x] Motor de busca vetorial com ChromaDB persistente em `src/rag/engine.py`
- [x] Chunking semântico baseado em cabeçalhos Markdown
- [x] Criação dos Runbooks corporativos em `knowledge_base/` (`runbook_auth_jwt.md`, `runbook_database_connection.md`, `runbook_ci_cd_guidelines.md`)
- [x] Suíte de avaliação quantitativa automatizada em `src/evals/eval_rag.py`

### Fase 4: AI Harness, CLI e CI/CD
- [x] Orquestrador ReAct com Auto-Healing e truncagem de contexto em `src/agent/harness.py`
- [x] Esquemas Pydantic tipados para Root Cause Analysis em `src/agent/schemas.py`
- [x] Empacotamento profissional com `pyproject.toml` e comando de console `devsre`
- [x] Pipeline de CI automatizado no GitHub Actions (`.github/workflows/ci.yml`)
- [x] Skill pedagógica interativa `.agent/skills/codebase-to-course/` para onboarding e estudo do portfólio

### Fase 5: Segurança e Hardening (CONCLUÍDA)
- [x] **Fix 1:** Blindagem contra Path Traversal em todas as ferramentas de arquivo (`is_relative_to`)
- [x] **Fix 2:** Sanitização e mascaramento de segredos/tokens em logs (`read_application_logs`)
- [x] **Fix 3:** Confirmação interativa (Human-in-the-Loop) para operações de escrita (`apply_patch`)
- [x] **Testes:** Bateria de testes de segurança cobrindo tentativas de invasão e escape de diretório

### Fase 6: Fine-Tuning com LoRA no Google Colab
- [x] Dataset estruturado de treinamento criado em `colab_finetuning/rca_dataset.jsonl`
- [x] Script de fine-tuning com QLoRA/LoRA pronto em `colab_finetuning/fine_tune_lora.py`
- [ ] Execução do treinamento no Google Colab Pro com GPU
- [ ] Avaliação comparativa de aderência ao formato (Modelo Base vs Modelo Fine-Tuned)

### Fase 7: Publicação e Apresentação de Portfólio
- [ ] Atualização final do `README.md` com badges de CI, métricas e diagrama arquitetural
- [ ] Criação do repositório público no GitHub com histórico de commits profissional
