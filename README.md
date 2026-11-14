# 🛠️ DevSRE-Companion: Autonomous AI SRE & Developer Copilot

[![CI Pipeline](https://github.com/usuario/devsre-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/usuario/devsre-copilot/actions)
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![Multi-Language](https://img.shields.io/badge/Polyglot-Java%20%7C%20Node%20%7C%20Go%20%7C%20Rust%20%7C%20Python-blueviolet.svg)
![MCP v1](https://img.shields.io/badge/MCP-FastMCP_v1-green.svg)
![LLM Engine](https://img.shields.io/badge/LLM-Gemini_3.8_Flash-orange.svg)
![RAG Hit Rate](https://img.shields.io/badge/RAG_Evals-100%25_Hit_Rate-brightgreen.svg)
![Security](https://img.shields.io/badge/Security-Defense_in_Depth-red.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)

Um assistente inteligente, autônomo e resiliente para **Engenharia de Software e SRE (Site Reliability Engineering)**, projetado como estudo prático e portfólio de alta maturidade em **AI Engineering**.

O **DevSRE-Companion** atua como um engenheiro autônomo: diante de bugs, falhas em testes de integração ou incidentes em produção, ele inspeciona o repositório, analisa logs sanitizados, consulta runbooks de arquitetura via busca semântica, aplica correções cirúrgicas com confirmação humana (*Human-in-the-Loop*) e valida as alterações com testes automatizados em um ciclo fechado de **Auto-Healing**.

---

## 🏗️ Arquitetura do Sistema

```text
                                  ┌────────────────────────┐
                                  │   CLI: `devsre`        │
                                  └───────────┬────────────┘
                                              │
                                              ▼
          ┌────────────────────────────────────────────────────────────────────────┐
          │                    AI HARNESS (RUNTIME, REACT & AUTO-HEALING)          │
          │  - Ciclo ReAct (Thought -> Action -> Observation)                      │
          │  - Google GenAI SDK (Gemini 3.8 Flash com AFC)                         │
          │  - Pydantic Structured Outputs (Root Cause Analysis - RCA)             │
          │  - Gestão e Truncagem de Janela de Contexto                            │
          └───────────────────┬────────────────────────────────┬───────────────────┘
                              │                                │
                              ▼                                ▼
                 ┌─────────────────────────┐      ┌─────────────────────────┐
                 │   RAG KNOWLEDGE ENGINE  │      │     MCP CLIENT & HUB    │
                 │   - ChromaDB Persistente│      │  (Model Context Prot.)  │
                 │   - Markdown Chunking   │      │  - JSON-RPC over STDIO  │
                 │   - 100% Hit Rate Evals │      └────────────┬────────────┘
                 └─────────────────────────┘                   │
                                                               ▼
                                                  ┌─────────────────────────┐
                                                  │    MCP SERVER LOCAL     │
                                                  │  - git status & diff    │
                                                  │  - pytest execution     │
                                                  │  - read_file & patch    │
                                                  │  - log secret redactor  │
                                                  └────────────┬────────────┘
                                                               │
                                                               ▼
                                                  ┌─────────────────────────┐
                                                  │   SECURITY GUARDRAILS   │
                                                  │  - Anti-Path Traversal  │
                                                  │  - Secret Masking Regex │
                                                  │  - Human-in-the-Loop    │
                                                  └─────────────────────────┘
```

---

## 🎯 Pilares Técnicos de AI Engineering

### 1. Model Context Protocol (MCP) Oficial
* Implementação desacoplada em [`src/mcp_server/server.py`](file:///F:/projetos/devsre-copilot/src/mcp_server/server.py) utilizando a especificação do FastMCP (`mcp<2.0.0`).
* Ferramentas expostas via protocolo padronizado JSON-RPC sobre STDIO:
  * `git_status`, `git_diff`: Auditoria do repositório alvo.
  * `list_directory`, `read_file`: Inspeção granular de arquivos com seleção de linhas.
  * `apply_patch`: Modificações cirúrgicas de código com validação de correspondência única.
  * `run_tests`: Execução poliglota com **detecção automática de ecossistema**: Java (Maven `mvn`/`mvnw` e Gradle `gradle`/`gradlew`), Node.js (`npm`/`yarn`/`pnpm`/`bun`), Go (`go test`), Rust (`cargo test`), .NET (`dotnet test`) e Python (`pytest`).
  * `read_application_logs`: Leitura de arquivos de log com sanitização em tempo real.

### 2. Advanced RAG & Avaliações Quantitativas (Evals)
* **Chunking Semântico Estruturado:** Diferente do chunking ingênuo por contagem de caracteres, o motor em [`src/rag/engine.py`](file:///F:/projetos/devsre-copilot/src/rag/engine.py) divide os runbooks em [`knowledge_base/`](file:///F:/projetos/devsre-copilot/knowledge_base/) respeitando a hierarquia Markdown (`##`, `###`), preservando regras de negócio e procedimentos íntegros.
* **Avaliação Automatizada:** Suíte em [`src/evals/eval_rag.py`](file:///F:/projetos/devsre-copilot/src/evals/eval_rag.py) que afere formalmente métricas de recuperação:
  * **Hit Rate de Fonte @ 2:** `100.0%`
  * **Hit Rate de Palavra-chave Técnica:** `100.0%`

### 3. AI Harness Resiliente com Auto-Healing
* Orquestrador em [`src/agent/harness.py`](file:///F:/projetos/devsre-copilot/src/agent/harness.py) utilizando o modelo `gemini-3.8-flash`.
* **Mecanismo de Auto-Healing:** Se um patch sugerido falhar na suíte de testes, o harness captura o traceback de erro, reinjeta o contexto na janela de raciocínio do modelo e executa até 3 tentativas de autocorreção antes de finalizar.
* **Saída Tipada Estruturada:** Utilização de esquemas Pydantic em [`src/agent/schemas.py`](file:///F:/projetos/devsre-copilot/src/agent/schemas.py) para garantir que diagnósticos de Causa Raiz sigam padrões estritos de auditoria.

### 4. Segurança e Defesa em Profundidade (Security Guardrails)
* **Anti-Path Traversal:** Verificação canônica com `pathlib.Path.is_relative_to()` em todas as operações de disco, impedindo ataques de escape de diretório (ex.: `../../etc/passwd`).
* **Sanitização de Segredos:** Redação determinística por Regex de chaves Google (`AIza...`), Bearer tokens, JWTs e credenciais de bancos de dados antes de serem transmitidos ao modelo ou gravados em logs.
* **Human-in-the-Loop Gate:** A ferramenta `apply_patch` gera um diff colorido e exige confirmação explícita interativa (`[s/N]`) do operador no terminal antes de alterar qualquer byte em disco.

### 5. Fine-Tuning Especializado com LoRA / QLoRA no Google Colab Pro
* Pipeline em [`colab_finetuning/`](file:///F:/projetos/devsre-copilot/colab_finetuning/) para adaptar modelos SLM (Gemma 2 2B / Llama 3.2 3B) para geração de RCA corporativo.
* Dataset curado com 10 incidentes reais de infraestrutura e engenharia de software (`rca_dataset.jsonl`).
* Notebook Jupyter pronto para Colab Pro (`devsre_lora_finetuning.ipynb`) com quantização NF4 de 4 bits, monitoramento de perda (*loss curve*) e teste de inferência comparativa.

### 6. Repositório AI-Native com Skill Pedagógica Integrada
* Contém a workspace skill [`.agent/skills/codebase-to-course/SKILL.md`](file:///F:/projetos/devsre-copilot/.agent/skills/codebase-to-course/SKILL.md), transformando o repositório em um ambiente de auto-onboarding que ensina toda a arquitetura através de aulas interativas e simulações de entrevistas técnicas.

---

## 📁 Estrutura do Projeto

```text
devsre-copilot/
├── .agent/
│   ├── rules/
│   │   └── devsre-guidelines.md      # Regras de engenharia e segurança
│   └── skills/
│       └── codebase-to-course/       # Skill interativa de ensino e onboarding
├── .github/
│   └── workflows/
│       └── ci.yml                    # Pipeline de CI/CD (Testes + Evals RAG)
├── colab_finetuning/
│   ├── devsre_lora_finetuning.ipynb  # Notebook de treinamento para Colab Pro
│   ├── fine_tune_lora.py             # Script standalone de treino com LoRA
│   ├── rca_dataset.jsonl             # Dataset curado de incidentes SRE
│   └── README.md                     # Guia de execução em GPU
├── knowledge_base/                   # Runbooks técnicos indexados no RAG
│   ├── runbook_auth_jwt.md
│   ├── runbook_ci_cd_guidelines.md
│   ├── runbook_database_connection.md
│   └── runbook_java_modernization.md # Guia de modernização e resolução de depreciações
├── src/
│   ├── agent/                        # AI Harness, ReAct loop e schemas Pydantic
│   ├── evals/                        # Avaliação quantitativa de precisão RAG
│   ├── mcp_server/                   # Servidor FastMCP e ferramentas poliglotas
│   ├── rag/                          # Motor vetorial ChromaDB e chunking semântico
│   ├── sample_app/                   # Microsserviço de teste com bug intencional
│   └── cli.py                        # Ponto de entrada da CLI devsre
├── tests/
│   ├── test_auth.py                  # Teste de contrato da aplicação de exemplo
│   ├── test_rag.py                   # Testes de integridade do chunking e busca vetorial
│   └── test_tools.py                 # Testes unitários, de segurança e detecção poliglota
├── pyproject.toml                    # Configuração de empacotamento PEP 621
├── requirements.txt                  # Dependências fixadas
├── TASKS.md                          # Painel persistente de controle de tarefas
└── README.md                         # Documentação completa
```

---

## 🚀 Instalação e Configuração

### Pré-requisitos
* Python 3.12+
* Chave de API do Google Gemini ([Google AI Studio](https://aistudio.google.com/))

### Passo a Passo
```bash
# 1. Clone o repositório
git clone https://github.com/usuario/devsre-copilot.git
cd devsre-copilot

# 2. Crie e ative o ambiente virtual
python -m venv .venv
.\.venv\Scripts\activate      # No Windows
# source .venv/bin/activate   # No Linux/macOS

# 3. Instale o pacote em modo de desenvolvimento
pip install -e .

# 4. Configure as credenciais
copy .env.example .env        # No Windows
# cp .env.example .env        # No Linux/macOS
# Adicione sua GEMINI_API_KEY no arquivo .env
```

---

## 💻 Guia de Uso da CLI `devsre`

### 1. Investigar e Auto-Corrigir um Incidente
```bash
devsre investigate --repo . "Investigue a falha no teste test_auth.py e proponha a correção"
```
O agente irá:
1. Inspecionar o Git e executar a suíte de testes.
2. Identificar a falha (`AssertionError: Header 'X-Token-Expired' is missing`).
3. Consultar a base RAG e recuperar a regra no runbook `runbook_auth_jwt.md`.
4. Exibir o diff e solicitar sua confirmação (`[s/N]`) para aplicar o patch.
5. Re-executar os testes para confirmar o **Auto-Healing**.
6. Emitir o relatório estruturado de Root Cause Analysis (RCA).

### 2. Rodar a Suíte de Avaliação do RAG
```bash
devsre eval
```

### 3. Re-indexar a Base de Runbooks
```bash
devsre rag-index
```

### 4. Executar a Suíte Completa de Testes
```bash
pytest -v
```

---

## 📊 Resultados e Métricas

| Componente | Métrica Avaliada | Resultado Obtido |
| :--- | :--- | :--- |
| **RAG Knowledge Engine** | Source Hit Rate @ 2 | **100.0%** |
| **RAG Knowledge Engine** | Keyword Hit Rate | **100.0%** |
| **Security Guardrails** | Bloqueio de Path Traversal & Dotfiles | **100% de Aprovação (.env, .git, ../ bloqueados)** |
| **Security Guardrails** | Redação de Segredos em Logs | **100% dos tokens mascarados (Google AQ/AIza, JWT, Bearer)** |
| **Polyglot Test Runner** | Detecção Multi-Linguagem | **Java (Maven/Gradle), Node, Go, Rust, .NET e Python** |
| **Suíte de Testes** | Cobertura Unitária e de Segurança | **31 aprovados, 1 xfailed (laboratório de incidente)** |

---

## 📜 Licença

Distribuído sob a licença **MIT**. Veja `LICENSE` para mais detalhes.
