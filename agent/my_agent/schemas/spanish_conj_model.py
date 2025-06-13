from pydantic import BaseModel, Field
from typing import Dict, Literal, Annotated

# Type definitions for better LLM understanding
NonPersonalForms = Literal[
    "infinitivo",
    "participio",
    "gerundio"
]
IndicativeTenses = Literal[
    "presente",
    "preterito perfecto simple",
    "preterito imperfecto",
    "preterito perfecto compuesto",
    "preterito pluscuamperfecto",
    "futuro",
    "futuro perfecto",
    "condicional",
    "condicional perfecto"
]
SubjunctiveTenses = Literal[
    "presente",
    "preterito imperfecto",
    "preterito perfecto compuesto",
    "preterito pluscuamperfecto",
    "futuro",
]

class SpanishConjugationForm(BaseModel):
    """Represents a complete set of conjugations for a specific tense."""
    yo: Annotated[str, Field(description="First person singular form")]
    tu: Annotated[str, Field(
        description="Second person singular informal form"
    )]
    el_ella_usted: Annotated[str, Field(
        description="Third person singular or formal singular form"
    )]
    nosotros_nosotras: Annotated[str, Field(
        description="First person plural form"
    )]
    vosotros_vosotras: Annotated[str, Field(
        description="Second person plural informal form"
    )]
    ellos_ellas_ustedes: Annotated[str, Field(
        description="Third person plural or formal plural form"
    )]


class SpanishVerbConjugation(BaseModel):
    """Complete conjugation table for a Spanish verb."""
    formas_no_personales: Annotated[Dict[NonPersonalForms, str], Field(
        description="The non-personal forms of the verb, i.e. infinitivo, participio, and gerundio"
    )]
    indicativo: Annotated[Dict[IndicativeTenses, SpanishConjugationForm], Field(
        description="""All indicative mood forms:
        - presente: Present tense
        - preterito perfecto simple: Simple past tense
        - preterito imperfecto: Past continuous/descriptive tense
        - preterito perfecto compuesto: Future tense
        - preterito pluscuamperfecto: Past perfect tense
        - futuro: Future tense
        - futuro perfecto: Future perfect tense
        - condicional: Conditional tense
        - condicional perfecto: Perfect conditional tense"""    
    )]
    subjuntivo: Annotated[Dict[SubjunctiveTenses, SpanishConjugationForm], Field(
        description="""Subjunctive mood forms:
        - presente: Present subjunctive
        - preterito imperfecto: Past subjunctive
        - preterito perfecto compuesto: Past perfect subjunctive
        - preterito pluscuamperfecto: Past pluperfect subjunctive
        - futuro: Future subjunctive"""
    )]


from langchain.prompts import PromptTemplate

spanish_conjugation_prompt = PromptTemplate.from_template("""
Given the following Spanish verb "{verb}", return its full conjugation table in this JSON format, like for the example verb "trabajar":

### Example
{{
  "formas_no_personales": {{
    "infinitivo": "trabajar",
    "participio": "trabajado",
    "gerundio": "trabajando"
  }},
  "indicativo": {{
    "presente": {{
      "yo": "trabajo",
      "tu": "trabajas",
      "el_ella_usted": "trabaja",
      "nosotros_nosotras": "trabajamos",
      "vosotros_vosotras": "trabajáis",
      "ellos_ellas_ustedes": "trabajan"
    }},
    "preterito perfecto simple": {{
      "yo": "trabaje",
      "tu": "trabajaste",
      "el_ella_usted": "trabajó",
      "nosotros_nosotras": "trabajamos",
      "vosotros_vosotras": "trabajasteis",
      "ellos_ellas_ustedes": "trabajaron"
    }},
    "preterito imperfecto": {{
      "yo": "trabajaba",
      "tu": "trabajabas",
      "el_ella_usted": "trabajaba",
      "nosotros_nosotras": "trabajábamos",
      "vosotros_vosotras": "trabajabais",
      "ellos_ellas_ustedes": "trabajaban"
    }},
    "preterito perfecto compuesto": {{
      "yo": "he trabajado",
      "tu": "has trabajado",
      "el_ella_usted": "ha trabajado",
      "nosotros_nosotras": "hemos trabajado",
      "vosotros_vosotras": "habeis trabajado",
      "ellos_ellas_ustedes": "han trabajado"
    }},
    "preterito pluscuamperfecto": {{
      "yo": "había trabajado",
      "tu": "habías trabajado",
      "el_ella_usted": "había trabajado",
      "nosotros_nosotras": "habíamos trabajado",
      "vosotros_vosotras": "habíais trabajado",
      "ellos_ellas_ustedes": "habían trabajado"
    }},
    "futuro": {{
      "yo": "trabajare",
      "tu": "trabajarás",
      "el_ella_usted": "trabajará",
      "nosotros_nosotras": "trabajaremos",
      "vosotros_vosotras": "trabajareis",
      "ellos_ellas_ustedes": "trabajarán"
    }},
    "futuro perfecto": {{
      "yo": "habre trabajado",
      "tu": "habrás trabajado",
      "el_ella_usted": "habrá trabajado",
      "nosotros_nosotras": "habremos trabajado",
      "vosotros_vosotras": "habreis trabajado",
      "ellos_ellas_ustedes": "habrán trabajado"
    }},
    "condicional": {{
      "yo": "trabajaría",
      "tu": "trabajarías",
      "el_ella_usted": "trabajaría",
      "nosotros_nosotras": "trabajaríamos",
      "vosotros_vosotras": "trabajaríais",
      "ellos_ellas_ustedes": "trabajarían"
    }},
    "condicional perfecto": {{
      "yo": "habría trabajado",
      "tu": "habrías trabajado",
      "el_ella_usted": "habría trabajado",
      "nosotros_nosotras": "habríamos trabajado",
      "vosotros_vosotras": "habríais trabajado",
      "ellos_ellas_ustedes": "habrían trabajado"
    }}
  }},
  "subjuntivo": {{
    "presente": {{
      "yo": "trabaje",
      "tu": "trabajes",
      "el_ella_usted": "trabaje",
      "nosotros_nosotras": "trabajemos",
      "vosotros_vosotras": "trabajeis",
      "ellos_ellas_ustedes": "trabajen"
    }},
    "preterito imperfecto": {{
      "yo": "trabajara",
      "tu": "trabajaras",
      "el_ella_usted": "trabajara",
      "nosotros_nosotras": "trabajáramos",
      "vosotros_vosotras": "trabajarais",
      "ellos_ellas_ustedes": "trabajaran"
    }},
    "preterito perfecto compuesto": {{
      "yo": "haya trabajado",
      "tu": "hayas trabajado",
      "el_ella_usted": "haya trabajado",
      "nosotros_nosotras": "hayamos trabajado",
      "vosotros_vosotras": "hayais trabajado",
      "ellos_ellas_ustedes": "hayan trabajado"
    }},
    "preterito pluscuamperfecto": {{
      "yo": "hubiera trabajado",
      "tu": "hubieras trabajado",
      "el_ella_usted": "hubiera trabajado",
      "nosotros_nosotras": "hubieramos trabajado",
      "vosotros_vosotras": "hubieras trabajado",
      "ellos_ellas_ustedes": "hubieran trabajado"
    }},
    "futuro": {{
      "yo": "trabajare",
      "tu": "trabajares",
      "el_ella_usted": "trabajare",
      "nosotros_nosotras": "trabajáremos",
      "vosotros_vosotras": "trabajareis",
      "ellos_ellas_ustedes": "trabajaren"
    }}
  }}
}}
###
                                                          
Return the conjugation table for the verb "{verb}" **IN THE SAME JSON FORMAT** and **including all forms and tenses**.
""")



