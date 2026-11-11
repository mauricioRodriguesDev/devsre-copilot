# 🛠️ DevSRE-Companion: Autonomous AI SRE & Developer Copilot

Um assistente inteligente e autônomo voltado para **Engenharia de Software e SRE (Site Reliability Engineering)**, projetado como estudo prático e portfólio para **AI Engineering**.

O objetivo do DevSRE-Companion é atuar como um engenheiro júnior/pleno automatizado: diante de bugs, falhas em testes ou quebras de pipeline, ele inspeciona o repositório, analisa logs, consulta runbooks e documentações internas e gera diagnósticos com planos de ação e correções sugeridas.

---

## 🏗️ Arquitetura do Sistema

```text
                                 ┌────────────────────────┐
                                 │   CLI / Interface Dev  │
                                 └───────────┬────────────┘
                                             │
                                             ▼
         ┌────────────────────────────────────────────────────────────────────────┐
         │                        AI HARNESS (RUNTIME & EVALS)                    │
         │  - Loop ReAct (Raciocínio + Ação)        - Truncagem de Contexto       │
         │  - Tratamento de Falhas & Retentativas   - Suíte de Avaliações (Evals) │
         └───────────────────┬────────────────────────────────┬───────────────────┘
                             │                                │
                             ▼                                ▼
                ┌─────────────────────────┐      ┌─────────────────────────┐
                │   RAG KNOWLEDGE ENGINE  │      │     MCP CLIENT & HUB    │
                │ (Documentações/Runbooks)│      │  (Model Context Prot.)  │
                └────────────┬────────────┘      └────────────┬────────────┘
                             │                                │
                    [Vector Store / Docs]                     ▼
                                                 ┌─────────────────────────┐
                                                 │    MCP SERVER LOCAL     │
                                                 │  - git status & diff    │
                                                 │  - pytest execution     │
                                                 │  - log inspection       │
                                                 └─────────────────────────┘
```

---

## 🎯 Pilares Práticos de AI Engineering Abordados

1. **Tool Calling & Function Calling:**
   * O LLM invoca ferramentas especializadas emitindo schemas JSON estruturados.
2. **Model Context Protocol (MCP):**
   * Criação de um servidor MCP próprio expondo ferramentas do ambiente de desenvolvimento (Git, testes, logs) de forma desacoplada e segura.
3. **Advanced RAG (Retrieval-Augmented Generation):**
   * Indexação de documentação técnica, decisões de arquitetura (ADRs) e runbooks com busca semântica para fundamentar diagnósticos e evitar alucinações.
4. **AI Harness & Resiliência:**
   * Orquestração do ciclo de vida do agente, auto-recuperação contra erros de ferramentas e controle de janela de contexto.
5. **Fine-Tuning com LoRA / QLoRA:**
   * Especialização de modelo leve (via Google Colab Pro / GPU) para a geração de relatórios de *Root Cause Analysis* (RCA) com schema estrito.
6. **Evals (Avaliações Automatizadas):**
   * Baterias de testes sintéticos para medir a precisão da recuperação do RAG e taxa de acerto do agente em cenários reais de bug.

---

## 📁 Estrutura de Pastas

```text
devsre-copilot/
├── src/
│   ├── mcp_server/      # Servidor MCP expondo Git, Pytest e Leitura de Logs
│   ├── rag/             # Engine de busca semântica, chunking e embeddings
│   ├── agent/           # Harness, loop de execução ReAct e controle de contexto
│   └── evals/           # Métricas de avaliação de RAG e assertividade de tools
├── knowledge_base/      # Runbooks, manuais e guias de arquitetura indexados
├── colab_finetuning/    # Notebooks de fine-tuning (LoRA) e dataset de treinamento
├── tests/               # Testes unitários do sistema
├── requirements.txt     # Dependências do projeto
├── .env.example         # Modelo de configuração de chaves de API
└── README.md            # Documentação completa
```

---

## 🚀 Como Executar

### Pré-requisitos
* Python 3.11+
* Chave de API do Google Gemini (Google AI Studio)

### Instalação
```bash
# Clone e entre no projeto
cd devsre-copilot

# Ative o ambiente virtual
.\.venv\Scripts\activate   # No Windows

# Instale em modo editável com o comando CLI devsre
pip install -e .

# Configure suas credenciais
copy .env.example .env
```

### Comandos da CLI `devsre`
```bash
# 1. Investigar falhas ou inspecionar qualquer repositório
devsre investigate --repo "caminho/do/projeto" "Investigue a falha no teste de autenticação"

# 2. Executar a suíte de avaliação (Evals) do RAG
devsre eval

# 3. Reindexar a base de conhecimento de Runbooks
devsre rag-index

# 4. Iniciar o servidor MCP local
devsre mcp-serve
```
