from typing import Literal

from pydantic import BaseModel, Field

# Simplified type definitions
NonPersonalForms = Literal["infinitivo", "participio", "gerundio"]
IndicativeTenses = Literal[
    "presente",
    "preterito_perfecto_simple",
    "preterito_imperfecto",
    "preterito_perfecto_compuesto",
    "preterito_pluscuamperfecto",
    "futuro",
    "futuro_perfecto",
    "condicional",
    "condicional_perfecto",
]
SubjunctiveTenses = Literal[
    "presente",
    "preterito_imperfecto",
    "preterito_perfecto_compuesto",
    "preterito_pluscuamperfecto",
    "futuro",
]


class SpanishConjugationForm(BaseModel):
    """Conjugation forms for all persons."""

    yo: str = Field(description="1st person singular")
    tu: str = Field(description="2nd person singular informal")
    el_ella_usted: str = Field(description="3rd person singular/formal")
    nosotros_nosotras: str = Field(description="1st person plural")
    vosotros_vosotras: str = Field(description="2nd person plural informal")
    ellos_ellas_ustedes: str = Field(description="3rd person plural/formal")


class SpanishVerbConjugation(BaseModel):
    """Spanish verb conjugation table."""

    formas_no_personales: dict[NonPersonalForms, str] = Field(
        description="infinitivo, participio, gerundio"
    )
    indicativo: dict[IndicativeTenses, SpanishConjugationForm] = Field(
        description="presente=present, preterito_perfecto_simple=simple past, preterito_imperfecto=imperfect past, preterito_perfecto_compuesto=present perfect, preterito_pluscuamperfecto=past perfect, futuro=future, futuro_perfecto=future perfect, condicional=conditional, condicional_perfecto=perfect conditional"
    )
    subjuntivo: dict[SubjunctiveTenses, SpanishConjugationForm] = Field(
        description="presente=present subjunctive, preterito_imperfecto=past subjunctive, preterito_perfecto_compuesto=present perfect subjunctive, preterito_pluscuamperfecto=past perfect subjunctive, futuro=future subjunctive"
    )
