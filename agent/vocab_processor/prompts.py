from typing import Optional


def add_quality_feedback_to_prompt(
    base_prompt: str,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
    quality_requirements: Optional[list[str]] = None,
) -> str:
    """Add quality feedback and requirements sections to a prompt."""

    requirements_section = ""
    if quality_requirements:
        requirements_section = "\n\n--- REQUIREMENTS ---\n"
        requirements_section += "\n".join(f"- {req}" for req in quality_requirements)

    feedback_section = ""
    has_feedback = quality_feedback or previous_issues or suggestions
    if has_feedback:
        feedback_section = "\n\n--- QUALITY FEEDBACK & RETRY INSTRUCTIONS ---\n"
        if quality_feedback:
            feedback_section += f"{quality_feedback}\n"

        if previous_issues:
            issues_text = "\n".join(f"- {issue}" for issue in previous_issues)
            feedback_section += f"\n**Identified Issues:**\n{issues_text}\n"

        if suggestions:
            suggestions_text = "\n".join(
                f"- {suggestion}" for suggestion in suggestions
            )
            feedback_section += (
                f"\n**MUST FOLLOW THESE SUGGESTIONS:**\n{suggestions_text}\n"
            )

    if suggestions or previous_issues:
        print()
        print("-" * 100)
        print("suggestions or previous_issues")
        print(suggestions)
        print(previous_issues)
        print("-" * 100)
        print()

    return base_prompt + requirements_section + feedback_section


class PromptTemplate:
    """Template for tool prompts that can be reconstructed by supervisor."""

    def __init__(self, base_prompt: str, quality_requirements: list[str]):
        self.base_prompt = base_prompt
        self.quality_requirements = quality_requirements

    def build_enhanced_prompt(
        self,
        quality_feedback: Optional[str] = None,
        previous_issues: Optional[list[str]] = None,
        suggestions: Optional[list[str]] = None,
        **kwargs,
    ) -> str:
        """Build the enhanced prompt with quality feedback."""
        formatted_prompt = self.base_prompt.format(**kwargs)

        # also format quality_requirements
        formatted_quality_requirements = [
            req.format(**kwargs) for req in self.quality_requirements
        ]

        return add_quality_feedback_to_prompt(
            formatted_prompt,
            quality_feedback,
            previous_issues,
            suggestions,
            formatted_quality_requirements,
        )


CLASSIFICATION_PROMPT_TEMPLATE = PromptTemplate(
    base_prompt="""Classify '{source_word}' (Language: {source_language}).
Part of speech one of: {part_of_speech_values}).

Extract the base form of the word, removing any articles, prefixes and temporal and possessive modifiers and any other prefixes or suffixes.

For source_article:
  - English: null (no articles needed)
  - German: der/die/das for nouns
  - Spanish: el/la/los/las for nouns
""",
    quality_requirements=[
        "Extract base word correctly, removing any articles or modifiers",
        "1-3 clear and natural {source_language} definitions that are distinct and common",
        "Note informal/slang usage and other important information in source_additional_info in {source_language}",
    ],
)


TRANSLATION_PROMPT_TEMPLATE = PromptTemplate(
    base_prompt="""Translate '{source_word}' ({source_language}→{target_language}). 

Source POS: {source_part_of_speech}
Usually, the target POS is the same as the source POS.

IMPORTANT: If the target word is a noun, use correct part of speech depending on the gender and target language {target_language}:
- English: "noun" (English has no grammatical gender)
- German: "masculine noun", "feminine noun", or "neuter noun" 
- Spanish: "masculine noun" or "feminine noun"

If the target word is a noun, provide one of the following articles depending on the gender and target language:
- English: null (no articles needed)
- German: der/die/das
- Spanish: el/la/los/las

Provide most common translation, appropriate POS, article if needed, and additional info for register/context.""",
    quality_requirements=[
        "Use correct part of speech for {target_language}",
        "Match the register and tone of the source word:",
        "- If source is informal/slang, provide informal translation",
        "- If source is vulgar, note this and provide appropriate equivalent",
        "For slang/colloquial words, provide the most natural equivalent learners would encounter",
        "Use target_additional_info to explain context, register, and regional usage in {source_language}",
        "For informal/vulgar words like 'huevada', consider translations like 'bullshit', 'crap', 'nonsense' and explain the register.",
        "Provide the english translation of the target word in 'english_word', including article if it is a proper noun or 'to' if it is a verb",
        "Provide only the base form of the translated source word in 'target_word' without any articles or other modifiers",
    ],
)

EXAMPLES_PROMPT_TEMPLATE = PromptTemplate(
    base_prompt="Create 3-4 natural examples using '{source_word}' ({source_language}) and '{target_word}' ({target_language}). Context in {source_language}.",
    quality_requirements=[
        "Natural, conversational examples",
        "Grammatically correct in both languages",
        "Natural translations",
        "Helpful context notes in the source language",
        "Show different use cases",
        "For articles and function words: Focus on showing how the word functions in context rather than exact grammatical correspondence. Different languages have different gender systems, so exact article matching is not always possible.",
        "For content words (nouns, verbs, adjectives, adverbs): Try to use the same grammatical meaning and part of speech ({source_part_of_speech} -> {target_part_of_speech}) for original and translated sentence.",
        "If exact grammatical correspondence is not possible due to linguistic differences, prioritize natural, helpful examples that demonstrate the word's usage clearly for language learners.",
    ],
)

SYNONYMS_PROMPT_TEMPLATE = PromptTemplate(
    base_prompt="""You are a linguistic expert providing synonyms for '{target_word}' ({target_language}, {target_part_of_speech}).

**Analysis and Instructions:**
1.  First, determine if direct, common synonyms for '{target_word}' exist in {target_language}.
2.  If no direct synonyms exist, you must add a note in the source language {source_language} to briefly explain why no direct synonym exists.
3.  If possible, provide at least 1 to a maximum 3 of the closest words or concepts.
4.  For each synonym, the explanation has to be in the source language {source_language} and clarify the nuances and differences of the synonym compared to '{target_word}'.

**Input Word:** '{target_word}'
""",
    quality_requirements=[
        "If there really are no synonyms, just return an empty list with the note that no direct synonyms exist.",
        "The synonyms list should contain the closest related concepts, not meta-commentary.",
        "If the synonym is very uncommon but valid, it should be noted in explanation.",
        "Explanations must clarify subtle differences in meaning and usage in the source language {source_language}.",
        "Try to avoid archaic or overly academic terms unless the source word is also of that nature.",
    ],
)

SYLLABLES_PROMPT_TEMPLATE = PromptTemplate(
    base_prompt="""Break '{target_word}' ({target_language}) into syllables. Provide a syllable list and a clear phonetic guide using the International Phonetic Alphabet (IPA).

**IMPORTANT RULES for {target_language}:**
- For Spanish verbs ending in '-ear', the 'e' and 'a' are in SEPARATE syllables, creating a hiatus.
- For Spanish verbs ending in '-uir', the 'ui' is a diphthong and stays in one syllable.
- For English words use American English related IPA and for Spanish words use Latin American related IPA.

Provide the breakdown for: '{target_word}'""",
    quality_requirements=[
        "Syllables must be correct for the target word {target_word} in {target_language}, following the rules provided, taking into account the possible original source language nuances.",
        "Phonetic guide should be accurate and related to the International Phonetic Alphabet (IPA).",
        "However, the most important point is that the phonetic guide helps the language learner with the pronunciation, if there are some deviations to IPA, it is not important.",
        "You dont have to be 100% accurate, also we put '[ ]' around the phonetic guide in a later step, so you dont have to worry about it.",
    ],
)

CONJUGATION_PROMPT_TEMPLATE = PromptTemplate(
    base_prompt="Create comprehensive conjugation table for {target_language} verb '{target_word}'. Include all essential forms learners need. Output JSON only.",
    quality_requirements=[
        "Follow natural, standard conjugation patterns for {target_language}",
        "All forms are grammatically correct and commonly used",
        "Include all required tenses and persons for {target_language}",
        "JSON structure matches the expected schema exactly",
    ],
)

MEDIA_SEARCH_QUERY_PROMPT_TEMPLATE = PromptTemplate(
    base_prompt="""For the English word '{english_word}' generate optimal search terms for finding relevant photos in Pexels.{context_info}

Word: {english_word}""",
    quality_requirements=[
        "Use 1-3 search terms, each containing 1-2 words maximum",
        "Focus on the core concept/meaning rather than exact word form",
        "For word variations use the base concept",
        "Prioritize terms that would work for related word forms",
        "For complex concepts, include specific terms that capture the essence",
        "Use the provided context to understand the word's specific meaning and generate more targeted search terms",
    ],
)

MEDIA_SELECTION_PROMPT_TEMPLATE = PromptTemplate(
    base_prompt="Choose best photo for '{source_word}' ({source_language}) → '{target_word}' ({target_language}). Translate the texts like in alt, explanation, memory_tip to the source language {source_language}. Photos: {photos}",
    quality_requirements=[
        "Choose relevant, clear photo",
        "Accurate {source_language} translations",
        "Connect image to word in memory tip",
        "Clear explanations",
        "Culturally appropriate",
    ],
)

VALIDATION_PROMPT_TEMPLATE = PromptTemplate(
    base_prompt="""You are an expert linguistic validator. For input '{word}' of source language (if provided) '{source_language}', with the aim to translate it to {target_language}:

Instructions:
- Keep the source_word exactly as provided by the user (preserve "to build", "la casa", etc.)
- Validate if the input is a valid word/phrase in any supported and possible source language {possible_source_languages}
- If the source_language is provided, validate if the input is a valid word/phrase in the source language
- Accept common articles, prefixes and modifiers (like "to", "la", "el", "der", "die", "das", "the") as part of valid input
- If the input is valid in any supported and possible source language {possible_source_languages}, mark as valid and return the detected language
- If the input is not valid/misspelled, suggest up to 3 real, high-frequency corrections with smallest spelling difference (edit distance up to 3)
- Only suggest corrections if they are common and actually exist in the possible source languages {possible_source_languages}
- **Never invent words.**
- **Never suggest rare words, names, or words in the target language.**
- **Never suggest the input word itself as a suggestion.**

Rules: No invented words, no rare words, no target language suggestions.
Supported: {all_languages}

Output JSON only.""",
    quality_requirements=[
        "Do only validate the word, also consider that it is a region specific word that is onlny spoken in parts of the Spanish, English or German speaking world.",
        "Do ONLY check if it is a valid word, DO NOT provide translations or any other kind of additional information.",
    ],
)
