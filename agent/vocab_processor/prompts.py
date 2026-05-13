from typing import Optional

from aws_lambda_powertools import Logger

logger = Logger(service="vocab-processor-prompts")


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
        logger.debug(
            "quality_feedback_retry_sections",
            suggestions=suggestions,
            previous_issues=previous_issues,
        )

    return base_prompt + requirements_section + feedback_section


def build_supervisor_tool_validation_prompt(
    *,
    source_word: str,
    source_language_display: str,
    target_word: str,
    target_language_display: str,
    tool_name: str,
    schema_json_block: str,
    assistant_prompt: str,
    assistant_output_json: str,
    quality_threshold: float,
) -> str:
    """Prompt for LLM supervisor that scores tool outputs against schema and instructions."""

    return f"""
            **VALIDATION TASK**
            You are a language learning expert. Your task is to validate the work of a language learning assistant. The overall goal of the assistant is to create accurate and informative vocabulary learning materials.

            Context:
            Source word: '{source_word}' ('{source_language_display}')
            Target word: '{target_word}' ('{target_language_display}')
            Assistant used tool: {tool_name}

            **Assistant's Role:**
            The assistant is a language learning expert. It is tasked with creating accurate and informative vocabulary learning materials.

            **Assistant's Output:**
            The assistant's output is a JSON object that conforms to the expected schema.


            **1. Expected Output Schema:**
            The output MUST conform to this Pydantic model schema:
            --- SCHEMA START ---
            {schema_json_block}
            --- SCHEMA END ---

            **2. Input Prompt:**
            This was the prompt given to the assistant:
            --- PROMPT START ---
            {assistant_prompt}
            --- PROMPT END ---

            **3. Assistant's Output:**
            Here is the assistants output using the above Pydantic model schema:
            --- JSON START ---
            {assistant_output_json}
            --- JSON END ---

            **Instructions for you, the Supervisor:**
            1.  **Schema Compliance:** First and foremost, check if the JSON output complies with the Pydantic schema. Are all required fields present? Are the data types correct? A stringified JSON output is also valid.

            2.  **Requirement Adherence:** Carefully read the 'REQUIREMENTS' section in the prompt. Has the assistant followed all instructions?

            3. **Content Quality:** The overall goal is to create an accurate and natural vocabulary learning material from '{source_word}' ('{source_language_display}') to the target word '{target_word}' ('{target_language_display}'). The content of the output should be accurate, informative and helpful for learning the target word.
            
            4. **Quality Score:** Rate the output on a scale of 1-10, where 10 is perfect. The score should reflect both schema compliance and adherence to the prompt's requirements as well as content quality. A low score should be given if either is not met.

            5.  **Issues and Suggestions:**
                - If the score is below {quality_threshold}, you MUST provide a list of found issues. Each issue should be a clear, concise statement describing a specific failure (e.g., "Field 'x' is missing", "Translation for 'y' is unnatural", "Source word "z" as a matter of fact does exist in the source language and is used in certain parts of the world").
                - If there are issues, you MUST also provide a list of suggestions for the assistant to improve the output on the next attempt. Suggestions should be actionable and directly related to the issues found.

            Your response MUST be a valid JSON object matching the ToolValidationResult schema.
            The score should be between 1 and 10 and should reflect the accuracy and quality of the output based on the given conditions. If the score is {quality_threshold} or higher, don't provide any issues or suggestions, just return the score.
            """


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
        "1-3 clear and natural dictionary-style '{source_language}' definitions of the source word '{source_word}' that are distinct and common, written in the language '{source_language}'",
        "IMPORTANT: Note informal/slang usage and other very important or special context, meaning and regional usage of the source word '{source_word}' in the language '{source_language}' in 'source_additional_info', written in the language '{source_language}'. If there is no highly important context, leave it empty.",
    ],
)

TRANSLATION_PROMPT_TEMPLATE = PromptTemplate(
    base_prompt="""Translate '{source_word}' ({source_language}→{target_language}).

Source part of speech (POS): {source_part_of_speech}
Target POS should generally match the source POS.

IMPORTANT rules for nouns based on target language ({target_language}) for "target_part_of_speech":
- English: Use "noun" (no grammatical gender)
- German: Use "masculine noun", "feminine noun", or "neuter noun"
- Spanish: Use "masculine noun" or "feminine noun"

If the target word is a noun, provide the appropriate definite article in "target_article":
- English: null (no article needed)
- German: 'der' / 'die' / 'das'
- Spanish: 'el' / 'la' / 'los' / 'las'

If the target word is a noun, include its plural form in 'target_plural_form' in the target language ({target_language}) including its article in the plural form ( for example "casa" -> "las casas").

Return the most common and natural translation, appropriate part of speech, required article (if applicable), and any relevant context or register in 'target_additional_info'.""",
    quality_requirements=[
        "Use region-appropriate vocabulary:",
        "- For English: Use American English",
        "- For Spanish: Use Latin American Spanish",
        "- For German: Use words commonly used in Germany",
        "Ensure the part of speech matches {target_language} norms.",
        "Respect the tone and register of the source word:",
        "- Informal/slang → informal/slang translation",
        "- Vulgar → appropriate vulgar equivalent (and mark it)",
        "- If formal → formal equivalent",
        "Provide natural learner-friendly equivalents for colloquial or slang expressions.",
        "Fill 'target_additional_info' with key contextual or regional notes (in the source language: {source_language}):",
        "- e.g., if usage is slang, informal, country-specific, or contextually bound",
        "- Leave empty if no relevant context",
        "For vulgar/informal terms (e.g., 'huevada'), use common equivalents like 'bullshit', 'crap', 'nonsense', and describe the tone and register appropriately.",
        "Fill 'english_word' with the English equivalent (include 'to' if verb, article if proper noun).",
        "Return only the **base form** of the translated word in 'target_word'—no articles or modifiers.",
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
    base_prompt="""You are a linguistic expert providing synonyms for the {target_part_of_speech} '{target_word}' in the language {target_language}.

**Analysis and Instructions:**
1.  First, determine if common synonyms for '{target_word}' exist in {target_language}.
2.  If possible, provide at least 1 to a maximum 3 of the most commonly words or concepts.
3.  For each synonym, the explanation has to be in the source language {source_language} and clarify the nuances and differences of the synonym compared to '{target_word}'. Make it clear and concise, should be maximum 3 sentences and no more than 100 words.

**Input Word:** '{target_word}'
""",
    quality_requirements=[
        "Try to start with the most commonly used synonyms in the target language {target_language}, if there are no common synonyms, try to provide synonyms that are very close in meaning.",
        "If there really are no synonyms, just return an empty list with the note that no direct synonyms exist.",
        "The synonyms list should contain the closest related concepts, not meta-commentary.",
        "If the synonym is very uncommon but valid, it should be noted in explanation.",
        "Explanations must clarify subtle differences in meaning and usage in the source language {source_language}.",
    ],
)

SYLLABLES_PROMPT_TEMPLATE = PromptTemplate(
    base_prompt="""You are a linguistic expert in the area of syllable breakdown and pronunciation. Break '{target_word}' ({target_language}) into syllables. Provide a syllable list and a simple, learner-friendly phonetic guide.

**IMPORTANT RULES for {target_language}:**
- For Spanish verbs ending in '-ear', the 'e' and 'a' are in SEPARATE syllables, creating a hiatus.
- For Spanish verbs ending in '-uir', the 'ui' is a diphthong and stays in one syllable.
- For German words ending in '-tion', the 'i' and 'o' are NEVER in separate syllables.
- For German, be mindful of final-obstruent devoicing: voiced stops ('b', 'd', 'g') at the end of a syllable are pronounced as their voiceless counterparts ('p', 't', 'k').

**PHONETIC GUIDE REQUIREMENTS:**
- Use SIMPLE, learner-friendly phonetic spellings (NO IPA symbols)
- Use common letters and combinations like: ah, eh, ee, oo, oh, uh
- Use 'k' for hard 'c' sounds, 'ts' for German 'z', 'sh' for 'sch', etc.
- Separate syllables with hyphens
- Important: Make it sound natural when read aloud by the native {target_language} speaker
- For English, use a American English pronunciation guide.
- For Spanish, use a Latin American pronunciation guide.
- For German, use a German (Hochdeutsch) pronunciation guide.

Provide the breakdown for: '{target_word}'""",
    quality_requirements=[
        "Syllables must be correct for the target word {target_word} in {target_language}, following the rules provided.",
        "Phonetic guide must use ONLY simple English letters and common combinations - NO IPA symbols whatsoever.",
        "CRITICAL: Use familiar English approximations that any English speaker can read aloud naturally.",
        "Keep phonetic guide simple and intuitive - prefer clarity and readability over technical precision.",
        "The phonetic guide should help English-speaking learners approximate the correct pronunciation.",
        "Use hyphens to separate syllables in the phonetic guide: syl-la-ble format.",
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
    base_prompt="""You are an expert linguistic validator. Your goal is to validate the input '{source_word}' and determine its language.

**CRITICAL LANGUAGE DETECTION RULES:**
1. If source_language is "unknown": You MUST detect which language the word belongs to from the possible source languages ({possible_source_languages}) and set source_language to that detected language.
2. If source_language is provided (not "unknown"): You MUST validate the word against that specific language only.

**Current Input:**
- Word to validate: '{source_word}'
- Source language provided: '{source_language}'
- Possible source languages: {possible_source_languages}

**Instructions:**
- Keep the input exactly as provided by the user
- If source_language is "unknown": Check if '{source_word}' is valid in any of the possible source languages ({possible_source_languages}). If valid, set source_language to the detected language.
- If source_language is provided (not "unknown"): Validate if '{source_word}' is a valid word/phrase in that specific language only.
- Accept common articles, prefixes and modifiers (like "to", "la", "el", "der", "die", "das", "the") as part of valid input
- Be aware that words can have multiple parts of speech. For example, 'build' can be a verb ('to build') or a noun ('the build'). Validate accordingly.
- ONLY in case of invalid word, provide suggestions and a message explaining the issue.
- ALWAYS set source_language to a valid language (English, Spanish, or German) - never leave it as None or "unknown".
""",
    quality_requirements=[
        "0. LANGUAGE DETECTION REQUIREMENT: You MUST always set source_language to a valid language (English, Spanish, or German). If the input source_language is 'unknown', detect the language from the possible source languages and set it. Never return None or 'unknown' for source_language.",
        "1. First, check if the word is a known regional or dialectal variant or used in special or technical contexts. If so, mark it as valid. Also consider that the word might be a proper noun or a name and include the provided articles and modifiers in your validation.",
        "2. If the word is not valid or misspelled in the detected source language, mark the word as invalid.",
        "3. If the word is invalid, provide a concise 'issue_message' explaining the issue in one sentence in the detected source language (not 'unknown') or in english if no source language is provided.",
        "4. For invalid words, suggest up to 3 unique, real, and correctly spelled alternative words in 'issue_suggestions'.",
        "5. If no good suggestions can be found, return an empty list for 'issue_suggestions' and state in the 'issue_message' that no alternatives were found.",
        "6. Do not invent words or provide translations. Only validate and suggest.",
        "7. IMPORTANT: Each suggested word must meet **all** of the following criteria:\n"
        "   - It must match the corresponding source language.\n"
        "   - It must be spelled grammatically correctly.\n"
        "   - If it is a **noun**, include the correct article (e.g., 'der', 'die', 'das' for German; 'la', 'lo' for Spanish; 'the' for English) in the suggested word string (e.g. 'the house').\n"
        "   - If it is a **verb** in English, prefix it with 'to' (e.g., 'to run').\n"
        "   - It must be **properly capitalized** according to the grammar rules of the source language.\n"
        "   - Think as if you had to validate the suggestion yourself - it should clearly be a valid word!",
    ],
)
