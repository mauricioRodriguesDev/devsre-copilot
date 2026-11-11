"""Script de Fine-Tuning com LoRA / QLoRA para execução no Google Colab.

Ajusta um modelo leve (Gemma 2 2B / Llama 3.2 3B) para a tarefa especializada de
Root Cause Analysis (RCA) para incidentes de engenharia de software.
"""

# Instalação das dependências no Google Colab:
# !pip install -q -U torch transformers datasets peft trl bitsandbytes accelerate

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

# 1. Configuração do Modelo Base
MODEL_NAME = "google/gemma-2-2b-it"  # Ou "meta-llama/Llama-3.2-3B-Instruct"
OUTPUT_DIR = "./devsre_rca_adapter"

print(f"--> Carregando tokenizer e modelo base: {MODEL_NAME}")

# Quantização de 4 bits para economia de VRAM (QLoRA)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.bfloat16,
)

model = prepare_model_for_kbit_training(model)

# 2. Configuração dos Adaptadores LoRA
lora_config = LoraConfig(
    r=16,                           # Posto da matriz LoRA
    lora_alpha=32,                  # Fator de escala
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# 3. Carregamento do Dataset de Treino
print("--> Carregando dataset: rca_dataset.jsonl")
dataset = load_dataset("json", data_files="rca_dataset.jsonl")

# 4. Hiperparâmetros de Treinamento
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    logging_steps=1,
    max_steps=50,
    fp16=False,
    bf16=True if torch.cuda.is_bf16_supported() else False,
    optim="paged_adamw_8bit",
    save_strategy="steps",
    save_steps=25,
)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset["train"],
    peft_config=lora_config,
    args=training_args,
)

# 5. Execução do Treinamento
print("--> Iniciando treinamento com LoRA...")
trainer.train()

# 6. Salvar os adaptadores finais
print(f"--> Treinamento finalizado! Salvando adaptadores em: {OUTPUT_DIR}")
trainer.model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print("--> Sucesso! Adaptadores LoRA prontos para inferência.")
