# 🧪 Módulo de Fine-Tuning: Especialista em RCA (Root Cause Analysis)

Este diretório contém o pipeline completo para especializar um modelo de linguagem leve (Small Language Model - SLM), como o **Gemma 2 (2B ou 9B)** ou **Llama 3.2 (3B)**, na geração estrita e técnica de relatórios de Causa Raiz para incidentes de engenharia de software e SRE.

---

## 🎯 Por que fazer Fine-Tuning aqui?
* **O problema:** Modelos de uso geral tendem a ser excessivamente prolixos, variam o formato a cada execução e frequentemente omitem campos vitais de auditoria exigidos pelo time de SRE.
* **A solução com LoRA/QLoRA:** Ajustar os pesos das camadas de projeção de atenção (`q_proj`, `k_proj`, `v_proj`, `o_proj`) com Low-Rank Adaptation (posto $r=16$, $\alpha=32$), ensinando o modelo a raciocinar segundo as melhores práticas de SRE e respeitar 100% dos esquemas estruturados.

---

## 📁 Arquivos do Módulo
1. `rca_dataset.jsonl`: Dataset com 10 incidentes reais e diversificados (JWT expirado, Pool overflow, Deadlock PostgreSQL, OOMKilled no Kubernetes, Cache Stampede Redis, Cascading failures gRPC, CORS, Esgotamento de disco e falhas TLS).
2. `devsre_lora_finetuning.ipynb`: Notebook Jupyter interativo com visualização da curva de perda (*loss curve*) e teste comparativo de inferência.
3. `fine_tune_lora.py`: Script standalone em Python para execução direta via terminal ou batch job.

---

## 🚀 Como executar no Google Colab Pro (com GPU)

### Opção 1: Execução Interativa via Notebook (Recomendado)
1. Acesse o [Google Colab](https://colab.research.google.com/).
2. Faça upload do notebook `devsre_lora_finetuning.ipynb`.
3. Certifique-se de selecionar um ambiente com **GPU (T4, L4 ou A100)**: `Ambiente de Execução` -> `Alterar tipo de ambiente de execução` -> `GPU`.
4. Faça upload do arquivo `rca_dataset.jsonl` na aba de arquivos do Colab.
5. Execute as células sequencialmente:
   * **Instalação:** `torch`, `transformers`, `peft`, `trl`, `bitsandbytes`.
   * **Treinamento:** QLoRA 4-bit NF4 com otimizador `paged_adamw_8bit`.
   * **Gráfico de Loss:** Plotagem da curva de convergência de erro.
   * **Inferência Comparativa:** Teste de generalização em um incidente inédito de filas SQS.
   * **Download:** Baixe o arquivo `devsre_rca_adapter.zip` gerado.

### Opção 2: Execução Direta via Script Python
```bash
# No ambiente do Google Colab:
pip install -q -U torch transformers datasets peft trl bitsandbytes accelerate
python fine_tune_lora.py
```

---

## 📊 Formato dos Dados de Treino (`rca_dataset.jsonl`)

Cada amostra segue o padrão Instruction-Tuning com as mensagens:
* **System:** Persona de especialista em SRE e exigência de formato estrito.
* **User:** Cenário do incidente + logs de erro capturados + regra do Runbook.
* **Assistant:** Relatório de RCA completo com título, severidade, causa técnica, código culpado vs código corrigido e plano preventivo.
