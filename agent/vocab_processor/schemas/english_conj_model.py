from typing import Dict, Literal

from pydantic import BaseModel, Field

# Simplified type definitions
NonPersonalForms = Literal["infinitive", "present_participle", "past_participle"]
IndicativeTenses = Literal[
    "present",
    "past",
    "present_perfect",
    "past_perfect",
    "present_perfect_progressive",
    "past_perfect_progressive",
    "future",
    "future_perfect",
    "future_progressive",
    "future_perfect_progressive",
    "conditional",
    "conditional_perfect",
]
SubjunctiveTenses = Literal["present", "past"]


class EnglishConjugationForm(BaseModel):
    """Conjugation forms for all persons."""

    I: str = Field(description="1st person singular")
    you: str = Field(description="2nd person singular")
    he_she_it: str = Field(alias="he/she/it", description="3rd person singular")
    we: str = Field(description="1st person plural")
    you_plural: str = Field(alias="you_plural", description="2nd person plural")
    they: str = Field(description="3rd person plural")


class EnglishVerbConjugation(BaseModel):
    """English verb conjugation table."""

    non_personal_forms: Dict[NonPersonalForms, str] = Field(
        description="infinitive, present participle, past participle"
    )
    indicative: Dict[IndicativeTenses, EnglishConjugationForm] = Field(
        description="present=simple present, past=simple past, present_perfect=have/has+past participle, past_perfect=had+past participle, present_perfect_progressive=have/has been+present participle, past_perfect_progressive=had been+present participle, future=will+infinitive, future_perfect=will have+past participle, future_progressive=will be+present participle, future_perfect_progressive=will have been+present participle, conditional=would+infinitive, conditional_perfect=would have+past participle"
    )
    subjunctive: Dict[SubjunctiveTenses, EnglishConjugationForm] = Field(
        description="present=present subjunctive, past=past subjunctive"
    )
