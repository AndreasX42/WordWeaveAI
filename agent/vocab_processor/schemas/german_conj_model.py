from typing import Annotated, Dict, Literal

from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field, constr

# Type definitions for better LLM understanding
NonPersonalForms = Literal["infinitive", "partizip präsens", "partizip perfekt"]
IndicativeTenses = Literal[
    "praesens", "praeteritum", "perfekt", "plusquamperfekt", "futur I", "futur II"
]
KonjunktivTenses = Literal["konjunktiv I", "konjunktiv II"]


# Pydantic models for German verb conjugation
class GermanConjugationForm(BaseModel):
    """Represents a complete set of conjugations for a specific tense."""

    ich: Annotated[str, Field(description="First person singular form")]
    du: Annotated[str, Field(description="Second person singular form")]
    er_sie_es: Annotated[str, Field(description="Third person singular form")]
    wir: Annotated[str, Field(description="First person plural form")]
    ihr: Annotated[str, Field(description="Second person plural form")]
    sie: Annotated[str, Field(description="Third person plural form")]


class GermanVerbConjugation(BaseModel):
    """Complete conjugation table for a German verb."""

    non_personal_forms: Annotated[
        NonPersonalForms,
        Field(
            description="The non-personal forms of the verb, i.e. infinitive, partizip praesens, and partizip perfekt"
        ),
    ]
    indikativ: Annotated[
        Dict[IndicativeTenses, GermanConjugationForm],
        Field(
            description="""All indicative forms:
        - praesens: Simple present tense
        - praeteritum: Simple past tense
        - perfekt: Present perfect (auxiliary + past participle)
        - plusquamperfekt: Past perfect (auxiliary + past participle)
        - futur I: Future tense (werde + infinitive)
        - futur II: Future perfect (werde + past participle + haben/sein)"""
        ),
    ]
    konjunktiv: Annotated[
        Dict[KonjunktivTenses, GermanConjugationForm],
        Field(
            description="""Konjunktiv forms (for indirect speech):
        - konjunktiv I: Konjunktiv I forms
        - konjunktiv II: Konjunktiv II forms"""
        ),
    ]


german_conjugation_prompt = PromptTemplate.from_template(
    """
Given the following German verb "{verb}", build a german conjugation table in the following JSON format like for the example verb "arbeiten":

{{
  "infinitiv": "arbeiten",
  "partizip_präsens": "arbeitend",
  "partizip_perfekt": "gearbeitet",
  "indikativ": {{
    "praesens": {{
      "ich": "arbeite",
      "du": "arbeitest",
      "er/sie/es": "arbeitet",
      "wir": "arbeiten",
      "ihr": "arbeitet",
      "sie": "arbeiten"
    }},
    "praeteritum": {{
      "ich": "arbeitete",
      "du": "arbeitetest",
      "er/sie/es": "arbeitete",
      "wir": "arbeiteten",
      "ihr": "arbeitetet",
      "sie": "arbeiteten"
    }},
    "perfekt": {{
      "ich": "habe gearbeitet",
      "du": "hast gearbeitet",
      "er/sie/es": "hat gearbeitet",
      "wir": "haben gearbeitet",
      "ihr": "habt gearbeitet",
      "sie": "haben gearbeitet"
    }},
    "plusquamperfekt": {{
      "ich": "hatte gearbeitet",
      "du": "hattest gearbeitet",
      "er/sie/es": "hatte gearbeitet",
      "wir": "hatten gearbeitet",
      "ihr": "hattet gearbeitet",
      "sie": "hatten gearbeitet"
    }},
    "futur I": {{
      "ich": "werde arbeiten",
      "du": "wirst arbeiten",
      "er/sie/es": "werde arbeiten",
      "wir": "werden arbeiten",
      "ihr": "werdet arbeiten",
      "sie": "werden arbeiten"
    }},
    "futur II": {{
      "ich": "werde gearbeitet haben",
      "du": "wirst gearbeitet haben",
      "er/sie/es": "werde gearbeitet haben",
      "wir": "werden gearbeitet haben",
      "ihr": "werdet gearbeitet haben",
      "sie": "werden gearbeitet haben"
    }}
  }},
  "konjunktiv": {{
    "konjunktiv I": {{
      "ich": "werde arbeiten",
      "du": "werdest arbeiten",
      "er/sie/es": "werde arbeiten",
      "wir": "werden arbeiten",
      "ihr": "werdet arbeiten",
      "sie": "werden arbeiten"
    }},
    "konjunktiv II": {{
      "ich": "würde gearbeitet haben",
      "du": "würdest gearbeitet haben",
      "er/sie/es": "würde gearbeitet haben",
      "wir": "würden gearbeitet haben",
      "ihr": "würdet gearbeitet haben",
      "sie": "würden gearbeitet haben"
    }}
  }}
}}

Return the conjugation table for the verb "{verb}" in the same JSON format.
"""
)
