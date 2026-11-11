# 🧪 Módulo de Fine-Tuning: Especialista em RCA (Root Cause Analysis)

Este diretório contém o pipeline para especializar um modelo de linguagem leve (Small Language Model - SLM), como o **Gemma 2 (2B ou 9B)** ou **Llama 3.2 (3B)**, na geração estrita e técnica de relatórios de Causa Raiz para incidentes de software.

---

## 🎯 Por que fazer Fine-Tuning aqui?
* **O problema:** Modelos gerais tendem a ser prolixos, inventar formatações diferentes a cada execução ou omitir campos essenciais exigidos pelo time de SRE.
* **A solução com LoRA:** Ajustar os pesos de atenção do modelo com adaptação de baixo posto (Low-Rank Adaptation), ensinando-o a raciocinar e estruturar diagnósticos técnicos com 100% de aderência ao formato da empresa, gastando fração mínima de memória de GPU.

---

## 🚀 Como executar no Google Colab (com sua conta Google Pro)

1. Abra o [Google Colab](https://colab.research.google.com/).
2. Conecte-se a um ambiente de execução com **GPU (T4, L4 ou A100)**.
3. Faça upload dos arquivos:
   * `rca_dataset.jsonl`
   * `fine_tune_lora.py` (ou execute as células correspondentes).
4. Execute o treinamento. Em uma GPU T4/L4, o treinamento leva menos de 5 minutos!

---

## 📊 Formato dos Dados de Treino (`rca_dataset.jsonl`)

Cada amostra segue a estrutura de mensagens padronizada:
* **System:** Persona de especialista em SRE e exigência de formato estrito.
* **User:** Cenário do incidente + logs de erro capturados + regra do Runbook.
* **Assistant:** Relatório de RCA completo com título, severidade, causa técnica, código culpado vs código corrigido e prevenção.
