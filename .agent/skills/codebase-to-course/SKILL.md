---
name: codebase-to-course
description: >-
  Transforma a codebase do DevSRE-Companion em um curso interativo e prático de Engenharia de IA e SRE.
  Use quando o usuário quiser estudar o projeto, entender profundamente a arquitetura (MCP, RAG, ReAct,
  Segurança, LoRA Fine-Tuning), preparar-se para entrevistas técnicas ou gerar um guia de estudos.
---

# 🎓 Codebase to Course: DevSRE-Companion Masterclass

Esta skill transforma o repositório **DevSRE-Companion** em um ambiente pedagógico imersivo de nível sênior. Ela foi desenhada para capacitar o autor do projeto a dominar 100% dos conceitos teóricos e práticos, além de fornecer o vocabulário exato para apresentar o projeto com maestria em entrevistas técnicas para vagas de **AI Engineer**, **Staff/Senior Software Engineer** ou **SRE / Platform Engineer**.

---

## 🧭 Metodologia Pedagógica: O Ciclo de 5 Passos

Ao iniciar qualquer módulo do curso, o agente atua como um **Mentor Técnico Sênior** e conduz cada aula seguindo o ciclo:

1. **Conceito & Fundamento Arquitetural (The "Why"):** O problema de engenharia do mundo real que a tecnologia resolve e as alternativas descartadas.
2. **Raio-X do Código Real (The "How"):** Navegação direta nos arquivos do projeto, dissecando funções, classes e decisões de implementação.
3. **Hands-on & Laboratório Prático:** Execução de comandos no terminal, injeção de cenários ou inspeção de saídas reais.
4. **Desafio Socrático (Knowledge Check):** Uma ou duas perguntas técnicas reflexivas para validar a fixação do conceito antes de avançar.
5. **Pitch de Entrevista Técnica:** Como responder à clássica pergunta: *"Como você desenhou e implementou essa parte do sistema?"*.

---

## 📚 Trilha de Módulos do Curso

### Módulo 1: O Protocolo MCP (Model Context Protocol) & Ferramentas Desacopladas
* **Objetivo:** Entender a revolução do MCP da Anthropic/Linux Foundation e como o FastMCP padroniza a interface entre modelos de linguagem e ferramentas de sistema.
* **Arquivos Chave:**
  * [`src/mcp_server/server.py`](file:///F:/projetos/devsre-copilot/src/mcp_server/server.py)
  * [`tests/test_tools.py`](file:///F:/projetos/devsre-copilot/tests/test_tools.py)
* **Tópicos Abordados:**
  * O que é MCP e por que ele substitui implementações proprietárias de Function Calling.
  * Comunicação via transporte STDIO e mensagens estruturadas JSON-RPC.
  * Criação de ferramentas com decorators `@mcp.tool()` e tipagem estrita com Type Hints e Docstrings (que alimentam o schema do modelo).
  * Gerenciamento de subprocessos com `subprocess.run` e `sys.executable` multiplataforma (Windows/Linux).
* **Desafio Prático:** Inspecionar o schema exportado pela ferramenta `read_file` e executar uma leitura de linhas específicas via CLI.

---

### Módulo 2: RAG Semântico Avançado & Avaliação Quantitativa (Evals)
* **Objetivo:** Dominar a recuperação contextual de Runbooks técnicos usando ChromaDB e a esteira de avaliação quantitativa automatizada.
* **Arquivos Chave:**
  * [`src/rag/engine.py`](file:///F:/projetos/devsre-copilot/src/rag/engine.py)
  * [`knowledge_base/`](file:///F:/projetos/devsre-copilot/knowledge_base/)
  * [`src/evals/eval_rag.py`](file:///F:/projetos/devsre-copilot/src/evals/eval_rag.py)
* **Tópicos Abordados:**
  * Por que o chunking ingênuo por tamanho de caracteres quebra o raciocínio de SRE: Chunking Semântico estruturado por seções Markdown (`##`, `###`).
  * Armazenamento vetorial com ChromaDB persistente e embeddings semânticos.
  * Métricas de Avaliação RAG: Definição de *Source Hit Rate @ K* e *Keyword Match Rate*.
  * Como a esteira de Evals garante 100% de precisão sem depender de "olhômetro" humano.
* **Desafio Prático:** Executar `devsre eval` e explicar o cálculo matricial que determinou os 100% de sucesso da base de conhecimento.

---

### Módulo 3: AI Harness, ReAct Loop & Auto-Healing
* **Objetivo:** Desvendar a mecânica interna do orquestrador autônomo que diagnostica incidentes e se auto-corrige em tempo real.
* **Arquivos Chave:**
  * [`src/agent/harness.py`](file:///F:/projetos/devsre-copilot/src/agent/harness.py)
  * [`src/agent/schemas.py`](file:///F:/projetos/devsre-copilot/src/agent/schemas.py)
  * [`src/sample_app/auth.py`](file:///F:/projetos/devsre-copilot/src/sample_app/auth.py)
  * [`tests/test_auth.py`](file:///F:/projetos/devsre-copilot/tests/test_auth.py)
* **Tópicos Abordados:**
  * O padrão **ReAct** (Reasoning + Acting): Como intercalar pensamento (`Thought`), invocação de ferramentas (`Action`) e análise de feedback (`Observation`).
  * Integração com o Google GenAI SDK (`google-genai`) e o modelo `gemini-3.8-flash`.
  * Auto-Healing: O que acontece quando o modelo aplica um patch que quebra os testes? Como o harness detecta o erro e reinjeta o traceback na janela de contexto.
  * Structured Outputs: Garantindo formato estrito com esquemas Pydantic (`RootCauseAnalysis`, `ActionItem`).
* **Desafio Prático:** Rodar a simulação do incidente de expiração de token JWT e acompanhar os passos do harness na correção do código.

---

### Módulo 4: Engenharia de Segurança & Defesa em Profundidade (Guardrails)
* **Objetivo:** Compreender a blindagem do agente contra vulnerabilidades do OWASP Top 10 para LLMs (Excessive Agency, Sensitive Data Exposure e Path Traversal).
* **Arquivos Chave:**
  * [`src/mcp_server/server.py`](file:///F:/projetos/devsre-copilot/src/mcp_server/server.py#L25-L65)
  * [`tests/test_tools.py`](file:///F:/projetos/devsre-copilot/tests/test_tools.py#L90-L160)
* **Tópicos Abordados:**
  * **Anti-Path Traversal:** Análise estrita de caminhos canônicos com `pathlib.Path.resolve()` e `is_relative_to()` no Python 3.12, bloqueando ataques como `../../Windows/System32`.
  * **Sanitização de Segredos:** Filtragem por Regex com redação determinística de Google API Keys (`AIza...`), tokens Bearer, JWTs e strings de conexão JDBC/Postgres.
  * **Human-in-the-Loop Gate:** Prevenção de alterações acidentais de arquivos com confirmação interativa no terminal antes de aplicar patches (`apply_patch`).
* **Desafio Prático:** Tentar burlar a ferramenta `read_file` simulando uma injeção de caminho e validar a captura da exceção `ValueError`.

---

### Módulo 5: Fine-Tuning Especializado com LoRA no Google Colab Pro
* **Objetivo:** Compreender quando e por que treinar um modelo em vez de usar apenas RAG ou Prompting, e como funciona o pipeline de adaptação de baixo posto (LoRA).
* **Arquivos Chave:**
  * [`colab_finetuning/rca_dataset.jsonl`](file:///F:/projetos/devsre-copilot/colab_finetuning/rca_dataset.jsonl)
  * [`colab_finetuning/fine_tune_lora.py`](file:///F:/projetos/devsre-copilot/colab_finetuning/fine_tune_lora.py)
  * [`colab_finetuning/README.md`](file:///F:/projetos/devsre-copilot/colab_finetuning/README.md)
* **Tópicos Abordados:**
  * A tríade de especialização de LLMs: *Prompt Engineering* vs *RAG* vs *Fine-Tuning*.
  * Mecânica matemática do LoRA: Decomposição de matrizes de peso ($W = W_0 + B \times A$), Rank $r$, Alpha $\alpha$ e preservação da base pré-treinada.
  * Construção e curadoria de dados de SRE em formato instruction-tuning (`instruction`, `input`, `output`).
  * Treinamento acelerado com Unsloth/PEFT e exportação de adaptadores GGUF/Hugging Face.
* **Desafio Prático:** Analisar a distribuição dos tokens no dataset `rca_dataset.jsonl` e calcular a economia de memória VRAM proporcionada pelo LoRA.

---

## 🛠️ Comandos e Modos de Interação

Ao interagir com esta skill, o usuário pode solicitar:

* **Iniciar o Curso do Início:** *"Vamos começar o curso pelo Módulo 1."*
* **Pular para um Módulo Específico:** *"Quero estudar o Módulo 3 sobre ReAct e Auto-Healing."*
* **Simulação de Entrevista Técnica:** *"Finja que você é um Tech Lead entrevistando para uma vaga SRE/AI e me faça 3 perguntas difíceis sobre a segurança e as ferramentas deste projeto."*
* **Gerar Apostila de Estudo:** *"Gere um arquivo `docs/ARCHITECTURE_STUDY_GUIDE.md` com o resumo executivo dos 5 módulos para eu revisar antes de entrevistas."*

---

## 💡 Diretrizes de Resposta do Mentor
* **Tom:** Didático, rigoroso tecnicamente, encorajador e pragmático.
* **Código Vivo:** Sempre vincule as explicações a trechos reais de código existentes no projeto através de links Markdown `[arquivo.py](file:///caminho#L1-L10)`.
* **Sem Alucinações:** Use apenas os componentes, bibliotecas e decisões que foram efetivamente implementadas na codebase.
* **Foco no Portfólio:** Aponte consistentemente como o conhecimento daquele módulo deve ser destacado no currículo, no LinkedIn ou no `README.md` do GitHub.
