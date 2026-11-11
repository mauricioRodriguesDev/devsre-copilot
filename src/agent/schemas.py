"""Esquemas de dados estruturados (Pydantic) para o DevSRE-Companion.

Garante que o relatório final de diagnóstico e Root Cause Analysis (RCA)
seja estritamente tipado, previsível e pronto para consumo por outros sistemas.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


class RootCauseAnalysisReport(BaseModel):
    """Relatório estruturado de análise de causa raiz de incidentes ou bugs."""

    incident_title: str = Field(
        description="Título conciso do incidente ou teste quebrado identificado."
    )
    severity: Literal["BAIXA", "MEDIA", "ALTA", "CRITICA"] = Field(
        description="Nível de gravidade do incidente de acordo com impacto no build/sistema."
    )
    root_cause_summary: str = Field(
        description="Explicação técnica clara e fundamentada da causa raiz do problema."
    )
    culprit_files: List[str] = Field(
        default_factory=list,
        description="Lista de arquivos ou módulos responsáveis pelo erro."
    )
    suggested_fix_diff: str = Field(
        description="Código de correção sugerido no formato unified diff ou bloco de código elucidativo."
    )
    prevention_steps: List[str] = Field(
        default_factory=list,
        description="Ações preventivas recomendadas para evitar recorrência do mesmo problema."
    )
