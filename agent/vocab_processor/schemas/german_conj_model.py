from typing import Literal

from pydantic import BaseModel, Field

# Simplified type definitions
NonPersonalForms = Literal[
    "infinitive",
    "partizip_praesens",
    "partizip_perfekt",
]
IndicativeTenses = Literal[
    "praesens", "praeteritum", "perfekt", "plusquamperfekt", "futur_i", "futur_ii"
]
SubjunctiveTenses = Literal["konjunktiv_i", "konjunktiv_ii", "konjunktiv_perfekt"]


class GermanConjugationForm(BaseModel):
    """Conjugation forms for all persons."""

    ich: str = Field(description="1st person singular")
    du: str = Field(description="2nd person singular")
    er_sie_es: str = Field(description="3rd person singular")
    wir: str = Field(description="1st person plural")
    ihr: str = Field(description="2nd person plural")
    sie: str = Field(description="3rd person plural")


class GermanVerbConjugation(BaseModel):
    """German verb conjugation table."""

    non_personal_forms: dict[NonPersonalForms, str] = Field(
        description="infinitive, present participle, past participle"
    )
    indikativ: dict[IndicativeTenses, GermanConjugationForm] = Field(
        description="praesens=present, praeteritum=simple past, perfekt=present perfect, plusquamperfekt=past perfect, futur_i=future, futur_ii=future perfect"
    )
    konjunktiv: dict[SubjunctiveTenses, GermanConjugationForm] = Field(
        description="konjunktiv_i=subjunctive I, konjunktiv_ii=subjunctive II, konjunktiv_perfekt=subjunctive perfect"
    )
