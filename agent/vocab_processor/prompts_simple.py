from typing import Optional


def add_quality_feedback_to_prompt(
    full_prompt: str,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> str:
    """Add quality feedback sections to a prompt (simplified version)."""

    if not (quality_feedback or previous_issues or suggestions):
        return full_prompt

    feedback_section = "\n\n--- QUALITY FEEDBACK & RETRY INSTRUCTIONS ---\n"

    if quality_feedback:
        feedback_section += f"{quality_feedback}\n"

    if previous_issues:
        issues_text = "\n".join(f"- {issue}" for issue in previous_issues)
        feedback_section += f"\n**Identified Issues:**\n{issues_text}\n"

    if suggestions:
        suggestions_text = "\n".join(f"- {suggestion}" for suggestion in suggestions)
        feedback_section += (
            f"\n**MUST FOLLOW THESE INSTRUCTION SET:**\n{suggestions_text}\n"
        )

    # Add debug printing like in original prompts.py
    if suggestions or previous_issues:
        print()
        print("ISSUES DETECTED" + "-" * 100)
        print(suggestions)
        print(previous_issues)
        print("-" * 100)
        print()

    return full_prompt + feedback_section


class PromptTemplate:
    """Simple template that just holds a complete prompt string."""

    def __init__(self, full_prompt: str):
        self.full_prompt = full_prompt
        # Keep these for backward compatibility
        self.base_prompt = full_prompt
        self.quality_requirements = []

    def build_enhanced_prompt(
        self,
        quality_feedback: Optional[str] = None,
        previous_issues: Optional[list[str]] = None,
        suggestions: Optional[list[str]] = None,
        **kwargs,
    ) -> str:
        """Build the enhanced prompt with quality feedback."""
        formatted_prompt = self.full_prompt.format(**kwargs)

        return add_quality_feedback_to_prompt(
            formatted_prompt,
            quality_feedback,
            previous_issues,
            suggestions,
        )


# Simplified, integrated prompt templates
CLASSIFICATION_PROMPT_TEMPLATE = PromptTemplate(
    full_prompt="""Classify '{source_word}' ({source_language}).
Part of speech: {part_of_speech_values}

**Task:**
1. Extract the base form, removing articles/prefixes/modifiers (if the source wourd is itself an article or some base form, leave it as is)
2. Provide 1-3 clear, natural dictionary definitions in {source_language}
3. Note any important context (slang, regional usage, etc.) in {source_language}

**Articles:**
- English: null (no articles needed)
- German: der/die/das for nouns
- Spanish: el/la/los/las for nouns

**Quality Requirements:**
- Extract base word correctly, removing any articles, prefixes, temporal and possessive modifiers, and any other prefixes or suffixes
- Provide 1-3 clear and natural dictionary-style definitions in {source_language} that are distinct and common
- **IMPORTANT:** Note informal/slang usage and other very important or special context, meaning, and regional usage of '{source_word}' in {source_language} in 'source_additional_info'. If there is no highly important context, leave it empty
- Definitions should be written in {source_language}
- Focus on the most common and relevant meanings
"""
)

TRANSLATION_PROMPT_TEMPLATE = PromptTemplate(
    full_prompt="""Translate '{source_word}' ({source_language} → {target_language}).
Source part of speech: {source_part_of_speech}

**Task:**
1. Provide the most common, natural translation
2. Use base form only (no articles/modifiers in target_word)
3. For nouns: provide correct article and plural form
4. Maintain tone/register (formal/informal/slang)
5. Add contextual notes in target_additional_info

**Part of Speech:**
- English: Use "noun" (no grammatical gender)
- German: Use "masculine noun", "feminine noun", or "neuter noun"
- Spanish: Use "masculine noun" or "feminine noun"

**Articles:**
- English: null (no articles needed)
- German: der/die/das for nouns
- Spanish: el/la/los/las for nouns

**Regional Preferences:**
- English: Use American English
- Spanish: Use Latin American Spanish
- German: Use standard German

**Quality Requirements:**
- Natural, region-appropriate translation
- Respect source word's tone and register:
  - Informal/slang → informal/slang translation
  - Vulgar → appropriate vulgar equivalent (and mark it)
  - Formal → formal equivalent
- Provide learner-friendly equivalents for colloquial or slang expressions
- For vulgar/informal terms (e.g., 'huevada'), provide common equivalents (e.g., 'bullshit', 'crap', 'nonsense') **and describe tone and register**
- **Ensure the part of speech matches {target_language} norms**
- Fill **'english_word'** with the English equivalent (include **'to'** if verb, article if proper noun)
- Fill 'target_additional_info' with key contextual or regional notes (in {source_language}):
  - e.g., if usage is slang, informal, country-specific, or contextually bound
  - Leave empty if no relevant context
- For nouns: include plural form in 'target_plural_form' with article (e.g., "casa" → "las casas")
- Base form only in target_word field
"""
)

EXAMPLES_PROMPT_TEMPLATE = PromptTemplate(
    full_prompt="""Create 3-4 natural examples using '{source_word}' ({source_language}) and '{target_word}' ({target_language}).

**Task:**
1. Show different contexts and use cases
2. Provide natural translations (not word-for-word)
3. Include helpful context notes in {source_language}
4. For grammar words: focus on functional usage
5. For content words: maintain part of speech when possible

**Quality Requirements:**
- Natural, conversational examples
- Grammatically correct in both languages
- Natural translations (not word-for-word)
- Helpful context notes in {source_language}
- Show varied use cases and different contexts
- **For articles and function words:** Focus on showing how the word functions in context rather than exact grammatical correspondence. Different languages have different gender systems, so exact article matching is not always possible
- **For content words (nouns, verbs, adjectives, adverbs):** Try to use the same grammatical meaning and part of speech ({source_part_of_speech} → {target_part_of_speech}) for original and translated sentences
- If exact grammatical correspondence is not possible due to linguistic differences, prioritize natural, helpful examples that demonstrate the word's usage clearly for language learners
"""
)

SYNONYMS_PROMPT_TEMPLATE = PromptTemplate(
    full_prompt="""Find synonyms for '{target_word}' ({target_part_of_speech}) in {target_language}.

**Analysis and Instructions:**
1. First, determine if common synonyms for '{target_word}' exist in {target_language}
2. If no common synonyms exist, you must add a note in {source_language} to briefly explain why no direct synonym exists (max 500 characters)
3. If possible, provide at least 1 to a maximum of 3 of the most commonly used words or concepts
4. For each synonym, the explanation must be in {source_language} and clarify the nuances and differences compared to '{target_word}'. Make it clear and concise (maximum 3 sentences, no more than 100 words)

**Task:**
1. Determine if common synonyms exist
2. If no synonyms: explain briefly in {source_language}
3. Provide 1-3 most common synonyms
4. Explain nuances/differences in {source_language} (max 100 words each)

**Quality Requirements:**
- Start with most common synonyms in {target_language}
- If no common synonyms, try to provide synonyms that are very close in meaning
- Clear explanations of differences in {source_language}
- If no synonyms exist, return empty list with explanation
- Focus on closest related concepts, not meta-commentary
- If synonyms are uncommon but valid, note this in explanation
- Explanations must concisely clarify subtle differences in meaning and usage and include special context, meaning, and regional usage, but must be concise (max 300 characters each)
"""
)

SYLLABLES_PROMPT_TEMPLATE = PromptTemplate(
    full_prompt="""Break '{target_word}' ({target_language}) into syllables with phonetic guide.

**Task:**
1. Provide correct syllable breakdown
2. Create simple phonetic guide using English letters
3. Use: ah, eh, ee, oo, oh, uh, k, ts, sh
4. Separate syllables with hyphens
5. NO IPA symbols - only English approximations

**Syllable Rules:**
- Spanish '-ear' verbs: 'e' and 'a' are SEPARATE syllables
- Spanish '-uir' verbs: 'ui' is a diphthong (single syllable)
- German '-tion': 'i' and 'o' are NEVER separate syllables
- German: final consonants change (b→p, d→t, g→k)

**Regional Preferences:**
- English: Use American English
- Spanish: Use Latin American Spanish
- German: Use standard German

**Quality Requirements:**
- Correct syllables for {target_language}
- Simple English letters only (NO IPA)
- Natural pronunciation when read aloud
- Hyphens to separate syllables
- Learner-friendly phonetic guide
"""
)

CONJUGATION_PROMPT_TEMPLATE = PromptTemplate(
    full_prompt="""Create conjugation table for {target_language} verb '{target_word}'.

**Task:**
1. Include all essential forms for learners
2. Follow standard conjugation patterns
3. Output valid JSON matching expected schema

**Quality Requirements:**
- Natural, standard conjugation patterns
- All forms grammatically correct
- Include required tenses/persons for {target_language}
- Valid JSON structure
"""
)

MEDIA_SEARCH_QUERY_PROMPT_TEMPLATE = PromptTemplate(
    full_prompt="""Generate search terms for '{english_word}' photos in Pexels.{context_info}

**Task:**
1. Use 1-3 search terms (1-2 words each)
2. Focus on core concept, not exact word form
3. Consider provided context for targeted results

**Quality Requirements:**
- Relevant to word meaning
- Effective for image search
- Use base concepts for variations
- Context-aware when provided
"""
)

MEDIA_SELECTION_PROMPT_TEMPLATE = PromptTemplate(
    full_prompt="""Choose best photo for '{source_word}' ({source_language}) → '{target_word}' ({target_language}).
Photos: {photos}

**Task:**
1. Select most relevant, clear photo
2. Translate alt/explanation/memory_tip to {source_language}
3. Create memory connection between image and word
4. Ensure cultural appropriateness

**Quality Requirements:**
- Relevant image selection
- Accurate translations to {source_language}
- Helpful memory connections
- Clear, culturally appropriate explanations
"""
)

VALIDATION_PROMPT_TEMPLATE = PromptTemplate(
    full_prompt="""Validate '{source_word}' and determine language.
Source language: '{source_language}'
Possible languages: {possible_source_languages}

**CRITICAL LANGUAGE DETECTION RULES:**
1. If source_language is "unknown": You MUST detect which language the word belongs to from the possible source languages and set source_language to that detected language
2. If source_language is provided (not "unknown"): Validate the word against that specific language only

**Task:**
1. If source_language is "unknown": detect correct language
2. If provided: validate against that language only
3. Accept articles, prefixes, modifiers
4. Consider multiple parts of speech
5. For invalid words: provide suggestions and clear message
6. **ALWAYS set source_language to valid language (never "unknown")**

**Instructions:**
- Keep the input exactly as provided by the user
- Accept common articles, prefixes and modifiers (like "to", "la", "el", "der", "die", "das", "the") as part of valid input
- Be aware that words can have multiple parts of speech (e.g., 'build' can be verb or noun)
- Check for regional/dialectal variants and technical contexts
- ONLY provide suggestions for invalid words

**Quality Requirements:**
- **LANGUAGE DETECTION REQUIREMENT:** You MUST always return a valid language (English, Spanish, or German) – never "unknown"
- Proper language detection when needed
- Accept regional/dialectal variants
- Clear error messages in detected language
- Up to 3 valid suggestions with correct articles/capitalization
- Every suggestion must:
  - Match the detected source language
  - Be spelled correctly
  - If the suggested word is a noun, include the correct article for the word in the language of the suggested word
  - If the suggested word is a verb and its language is English, prefix the verb with 'to'
  - Use proper capitalisation according to grammar rules
  - Be a clearly valid word that would pass validation itself
- If no good suggestions exist, return empty list and explain in issue_message
- Do not invent words or provide translations - only validate and suggest
- Never return "unknown" for source_language
"""
)
