from pydantic import BaseModel, Field, constr
from typing import Dict, Literal, Annotated
from langchain.prompts import PromptTemplate

# Type definitions for better LLM understanding
NonPersonalForms = Literal[
    "infinitive",
    "present participle",
    "past participle"
]
IndicativeTenses = Literal[
    "present",
    "past",
    "present perfect",
    "past perfect",
    "present perfect progressive",
    "past perfect progressive",
    "future",
    "future perfect"
]
SubjunctiveTenses = Literal["present", "past"]

class EnglishConjugationForm(BaseModel):
    """Represents a complete set of conjugations for a specific tense."""
    I: Annotated[str, Field(description="First person singular form")]
    you: Annotated[str, Field(description="Second person singular form")]
    he_she_it: Annotated[str, Field(
        alias="he/she/it",
        description="Third person singular form"
    )]
    we: Annotated[str, Field(description="First person plural form")]
    you_plural: Annotated[str, Field(
        alias="you (plural)",
        description="Second person plural form"
    )]
    they: Annotated[str, Field(description="Third person plural form")]


class EnglishVerbConjugation(BaseModel):
    """Complete conjugation table for an English verb."""
    non_personal_forms: Annotated[Dict[NonPersonalForms, str], Field(
        description="The non-personal forms of the verb, i.e. infinitive, present participle, and past participle"
    )]
    indicative: Annotated[Dict[IndicativeTenses, EnglishConjugationForm], Field(
        description="""All indicative mood forms:
        - present: Simple present tense (adds -s for third person singular)
        - past: Simple past tense (usually -ed for regular verbs)
        - present perfect: Present perfect (have/has + past participle)
        - past perfect: Past perfect (had + past participle)
        - present perfect progressive: Present perfect progressive (have/has been + past participle)
        - past perfect progressive: Past perfect progressive (had been + past participle)
        - future: Future tense (will + infinitive)
        - future perfect: Future perfect (will have + past participle)"""
    )]
    subjunctive: Annotated[Dict[SubjunctiveTenses, EnglishConjugationForm], Field(
        description="""Subjunctive mood forms:
        - present: Present subjunctive (same as infinitive)
        - past: Past subjunctive (same as past tense)"""
    )]



english_conjugation_prompt = PromptTemplate.from_template("""
Given the following English verb "{verb}", build a english conjugation table in this JSON format, like for the example verb "work":

{{
  "infinitive": "work",
  "present_participle": "working",
  "past_participle": "worked",
  "indicative": {{
    "simple present": {{
      "I": "work",
      "you": "work",
      "he/she/it": "works",
      "we": "work",
      "you (plural)": "work",
      "they": "work"
    }},
    "simple past": {{
      "I": "worked",
      "you": "worked",
      "he/she/it": "worked",
      "we": "worked",
      "you (plural)": "worked",
      "they": "worked"
    }},
    "present perfect": {{
      "I": "have worked",
      "you": "have worked",
      "he/she/it": "has worked",
      "we": "have worked",
      "you (plural)": "have worked",
      "they": "have worked"
    }},
    "past perfect": {{
      "I": "had worked",
      "you": "had worked",
      "he/she/it": "had worked",
      "we": "had worked",
      "you (plural)": "had worked",
      "they": "had worked"
    }},
    "present perfect progressive": {{
      "I": "have been working",
      "you": "have been working",
      "he/she/it": "has been working",
      "we": "have been working",
      "you (plural)": "have been working",
      "they": "have been working"
    }},
    "past perfect progressive": {{
      "I": "had been working",
      "you": "had been working",
      "he/she/it": "had been working",
      "we": "had been working",
      "you (plural)": "had been working",
      "they": "had been working"
    }},
    "future": {{
      "I": "will work",
      "you": "will work",
      "he/she/it": "will work",
      "we": "will work",
      "you (plural)": "will work",
      "they": "will work"
    }},
    "future perfect": {{
      "I": "will have worked",
      "you": "will have worked",
      "he/she/it": "will have worked",
      "we": "will have worked",
      "you (plural)": "will have worked",
      "they": "will have worked"
    }}
  }},
  "subjunctive": {{
    "present": {{
      "I": "work",
      "you": "work",
      "he/she/it": "work",
      "we": "work",
      "you (plural)": "work",
      "they": "work"
    }},
    "past": {{
      "I": "worked",
      "you": "worked",
      "he/she/it": "worked",
      "we": "worked",
      "you (plural)": "worked",
      "they": "worked"
    }}
  }},
}}

Return the conjugation table for the verb "{verb}" in the same JSON format.
""")