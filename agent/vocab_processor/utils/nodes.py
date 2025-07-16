import json

from aws_lambda_powertools import Logger

from vocab_processor.tools import (
    get_classification,
    get_conjugation,
    get_examples,
    get_media,
    get_pronunciation,
    get_syllables,
    get_synonyms,
    get_translation,
    validate_word,
)
from vocab_processor.utils.state import VocabState
from vocab_processor.utils.supervisor import LLMRouter, TaskType, supervisor

logger = Logger(service="vocab-processor")
logger.setLevel("ERROR")


def _convert_to_dict(result: any) -> dict:
    """Convert a Pydantic model or other object to a dictionary."""
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "__dict__"):
        return result.__dict__
    if isinstance(result, dict):
        return result
    return {"result": result}


def _create_quality_result(
    result_dict: dict, tool_name: str, approved: bool, score: float
) -> dict:
    """Create standardized quality result with tool-specific approval and score."""
    return {
        **result_dict,
        f"{tool_name}_quality_approved": approved,
        f"{tool_name}_quality_score": score,
    }


def _create_fallback_result(tool_name: str, inputs: dict, error_msg: str) -> dict:
    """Create fallback result for failed tools."""
    from vocab_processor.utils.supervisor import create_fallback_result

    fallback = create_fallback_result(tool_name, inputs, error_msg)
    return _create_quality_result(fallback, tool_name, False, 0.0)


async def execute_with_quality_gate(
    state: VocabState, tool_func, tool_name: str, task_type: TaskType, inputs: dict
) -> dict:
    """Execute a tool with supervisor quality control and retry logic."""

    # Skip quality gate for pronunciation tool
    if tool_name == "pronunciation":
        return await execute_without_quality_gate(tool_func, tool_name, inputs)

    # Get current retry count
    retry_count_field = f"{tool_name}_retry_count"
    retry_count = getattr(state, retry_count_field, 0)

    # Select appropriate model
    llm_model = LLMRouter.get_model_for_task(task_type, retry_count)

    # Add model selection to inputs if supported
    if "llm_provider" in inputs:
        inputs["llm_provider"] = llm_model

    try:
        # Execute the tool
        response = await tool_func.ainvoke(inputs)

        result = getattr(response, "result", response)
        prompt = getattr(response, "prompt", None)
        result_dict = _convert_to_dict(result)

        # Validate result quality
        validation_result = await supervisor.validate_tool_output(
            tool_name, result_dict, state, prompt
        )

        print()
        print("-" * 100)
        print("tool_name", tool_name)
        print("result_dict", result_dict)
        print("validation_result", validation_result)
        print("-" * 100)
        print()

        # Log quality results efficiently
        logger.info(
            f"{tool_name}_quality_check",
            score=validation_result.score,
            issues_count=len(validation_result.issues),
            retry_count=retry_count,
        )

        # Check if quality meets threshold
        quality_passed = validation_result.score >= supervisor.quality_threshold

        if quality_passed:
            return _create_quality_result(
                result_dict, tool_name, True, validation_result.score
            )

        # Quality failed, plan retry
        retry_strategy = await supervisor.plan_retry_strategy(
            tool_name, validation_result, state
        )

        if retry_strategy.should_retry:
            # Increment retry count and retry
            updated_state = state.model_copy()
            setattr(updated_state, retry_count_field, retry_count + 1)

            # Apply adjusted inputs
            adjusted_inputs = {**inputs, **retry_strategy.adjusted_inputs}

            logger.info(
                f"{tool_name}_retry",
                retry_count=retry_count + 1,
                reason=retry_strategy.retry_reason,
            )

            # Recursive retry with adjusted inputs
            return await execute_with_quality_gate(
                updated_state, tool_func, tool_name, task_type, adjusted_inputs
            )

        # Max retries reached, return failure
        logger.error(
            f"{tool_name}_max_retries_reached",
            issues=validation_result.issues,
            final_score=validation_result.score,
        )

        error_msg = f"Quality threshold not met after {supervisor.max_retries} retries"
        return _create_fallback_result(tool_name, inputs, error_msg)

    except Exception as e:
        logger.error(
            f"{tool_name}_execution_failed",
            error=(
                json.dumps(_convert_to_dict(e), default=str)
                if hasattr(e, "__dict__")
                else str(e)
            ),
            retry_count=retry_count,
        )
        return _create_fallback_result(tool_name, inputs, str(e))


async def execute_without_quality_gate(tool_func, tool_name: str, inputs: dict) -> dict:
    """Execute a tool without quality gate validation (for reliable tools like pronunciation)."""

    try:
        # Execute the tool directly
        response = await tool_func.ainvoke(inputs)
        result_dict = _convert_to_dict(getattr(response, "result", response))

        logger.info(f"{tool_name}_executed_successfully")

        return result_dict

    except Exception as e:
        logger.error(
            f"{tool_name}_execution_failed",
            error=(
                json.dumps(_convert_to_dict(e), default=str)
                if hasattr(e, "__dict__")
                else str(e)
            ),
        )
        return _create_fallback_result(tool_name, inputs, str(e))


async def node_validate_source_word(state: VocabState) -> VocabState:
    """Validate the source word for spelling, ambiguity, and clarity."""

    inputs = {
        "source_word": state.source_word,
        "source_language": state.source_language,
        "target_language": state.target_language,
    }

    try:
        # Execute validation tool directly first to get business logic result
        response = await validate_word.ainvoke(inputs)
        result_dict = _convert_to_dict(response.result)

        logger.info(
            "validation_result",
            word=state.source_word,
            is_valid=result_dict.get("is_valid", False),
            source_language=(
                str(result_dict.get("source_language"))
                if result_dict.get("source_language")
                else None
            ),
            validation_message=result_dict.get("issue_message"),
            suggestions_count=(
                len(result_dict.get("issue_suggestions", []))
                if result_dict.get("issue_suggestions")
                else 0
            ),
        )

        # If validation failed, return immediately with clear error information
        if not result_dict.get("is_valid", False):
            error_message = result_dict.get("issue_message", "Word validation failed")
            suggestions = result_dict.get("issue_suggestions", [])

            logger.warning(
                "validation_failed",
                word=state.source_word,
                reason=error_message,
                suggestions=suggestions,
                suggestions_count=len(suggestions) if suggestions else 0,
            )

            return {
                "validation_passed": False,
                "validation_issue": error_message,
                "validation_suggestions": suggestions,
                "validation_quality_approved": False,  # Failed validation is not a quality issue
                "validation_quality_score": 0.0,
            }

        # If validation passed, run through quality gate for additional validation
        quality_result = await execute_with_quality_gate(
            state, validate_word, "validation", TaskType.VALIDATION, inputs
        )

        return {
            "validation_passed": True,
            "source_language": result_dict.get("source_language"),
            "validation_quality_approved": quality_result.get(
                "validation_quality_approved", False
            ),
            "validation_quality_score": quality_result.get(
                "validation_quality_score", 0.0
            ),
        }

    except Exception as e:
        logger.error("validation_execution_failed", error=str(e))
        return {
            "validation_passed": False,
            "validation_issue": f"Validation failed due to system error: {str(e)}",
            "validation_suggestions": [],
            "validation_quality_approved": False,
            "validation_quality_score": 0.0,
        }


async def node_get_classification(state: VocabState) -> VocabState:
    """Classify the source word for part of speech and definitions, then check if it exists."""
    inputs = {
        "source_word": state.source_word,
        "source_language": state.source_language,
        "target_language": state.target_language,
    }

    # Execute with quality gate
    result = await execute_with_quality_gate(
        state, get_classification, "classification", TaskType.CLASSIFICATION, inputs
    )

    logger.debug(
        "classification_result",
        source_word=result.get("source_word"),
        source_definition=result.get("source_definition"),
        source_part_of_speech=result.get("source_part_of_speech"),
        source_article=result.get("source_article"),
        word_exists=result.get("word_exists", False),
        quality_approved=result.get("classification_quality_approved", False),
        quality_score=result.get("classification_quality_score", 0.0),
    )

    return {
        "source_word": result.get("source_word"),
        "source_definition": result.get("source_definition"),
        "source_part_of_speech": result.get("source_part_of_speech"),
        "source_article": result.get("source_article"),
        "source_additional_info": result.get("source_additional_info"),
        "word_exists": result.get("word_exists", False),
        "existing_item": result.get("existing_item"),
        "classification_quality_approved": result.get(
            "classification_quality_approved", False
        ),
        "classification_quality_score": result.get("classification_quality_score", 0.0),
    }


async def node_get_translation(state: VocabState) -> VocabState:
    """Translate the word to the target language."""
    inputs = {
        "source_word": state.source_word,
        "source_language": state.source_language,
        "target_language": state.target_language,
        "source_part_of_speech": state.source_part_of_speech,
    }

    # Execute with quality gate
    result = await execute_with_quality_gate(
        state, get_translation, "translation", TaskType.TRANSLATION, inputs
    )

    logger.debug(
        "translation_result",
        word=state.source_word,
        target_word=result.get("target_word"),
        target_part_of_speech=result.get("target_part_of_speech"),
        target_article=result.get("target_article"),
        quality_approved=result.get("translation_quality_approved", False),
        quality_score=result.get("translation_quality_score", 0.0),
    )

    return {
        "target_word": result.get("target_word"),
        "target_part_of_speech": result.get("target_part_of_speech"),
        "target_article": result.get("target_article"),
        "target_additional_info": result.get("target_additional_info"),
        "english_word": result.get("english_word"),
        "translation_quality_approved": result.get(
            "translation_quality_approved", False
        ),
        "translation_quality_score": result.get("translation_quality_score", 0.0),
    }


async def node_get_synonyms(state: VocabState) -> VocabState:
    """Fetch synonyms for the word."""
    inputs = {
        "target_word": state.target_word,
        "source_language": state.source_language,
        "target_language": state.target_language,
        "target_part_of_speech": state.target_part_of_speech,
    }

    # Execute with quality gate
    result = await execute_with_quality_gate(
        state, get_synonyms, "synonyms", TaskType.SYNONYMS, inputs
    )

    logger.debug(
        "synonyms_result",
        word=state.target_word,
        synonyms=result.get("synonyms", []),
        quality_approved=result.get("synonyms_quality_approved", False),
        quality_score=result.get("synonyms_quality_score", 0.0),
    )

    return {
        "synonyms": result.get("synonyms", []),
        "synonyms_quality_approved": result.get("synonyms_quality_approved", False),
        "synonyms_quality_score": result.get("synonyms_quality_score", 0.0),
    }


async def node_get_syllables(state: VocabState) -> VocabState:
    """Generate syllable breakdown for the target word."""
    inputs = {
        "target_word": state.target_word,
        "target_language": state.target_language,
    }

    # Execute with quality gate
    result = await execute_with_quality_gate(
        state, get_syllables, "syllables", TaskType.SYLLABLES, inputs
    )

    logger.debug(
        "syllables_result",
        word=state.target_word,
        syllables=result.get("syllables", []),
        phonetic_guide=result.get("phonetic_guide", ""),
        quality_approved=result.get("syllables_quality_approved", False),
        quality_score=result.get("syllables_quality_score", 0.0),
    )

    return {
        "target_syllables": result.get("syllables", []),
        "syllables_quality_approved": result.get("syllables_quality_approved", False),
        "target_phonetic_guide": result.get("phonetic_guide", ""),
        "syllables_quality_score": result.get("syllables_quality_score", 0.0),
    }


async def node_get_pronunciation(state: VocabState) -> VocabState:
    """Get pronunciation audio for the word."""
    inputs = {
        "target_word": state.target_word,
        "target_syllables": state.target_syllables or [],
        "target_language": state.target_language,
    }

    # Execute without quality gate (reliable ElevenLabs API)
    result = await execute_without_quality_gate(
        get_pronunciation, "pronunciation", inputs
    )

    logger.debug(
        "pronunciation_result",
        word=state.target_word,
        pronunciations=result,
    )

    return {
        "pronunciations": result,
    }


async def node_get_media(state: VocabState) -> VocabState:
    """Get visual media for the word."""
    inputs = {
        "source_word": state.source_word,
        "target_word": state.target_word,
        "english_word": state.english_word,
        "source_language": state.source_language,
        "target_language": state.target_language,
        "source_definition": state.source_definition,
        "target_additional_info": state.target_additional_info,
    }

    # Execute with quality gate
    result = await execute_with_quality_gate(
        state, get_media, "media", TaskType.MEDIA_SELECTION, inputs
    )

    logger.debug(
        "media_result",
        word=state.source_word,
        media=result.get("media", None),
        search_query=result.get("search_query", []),
        media_reused=result.get("media_reused", False),
        quality_approved=result.get("media_quality_approved", False),
        quality_score=result.get("media_quality_score", 0.0),
    )

    return {
        "media": result.get("media", None),
        "media_ref": result.get("media_ref", None),
        "search_query": result.get("search_query", []),
        "media_reused": result.get("media_reused", False),
        "media_quality_approved": result.get("media_quality_approved", False),
        "media_quality_score": result.get("media_quality_score", 0.0),
    }


async def node_get_examples(state: VocabState) -> VocabState:
    """Generate example sentences."""
    inputs = {
        "source_word": state.source_word,
        "target_word": state.target_word,
        "source_language": state.source_language,
        "target_language": state.target_language,
        "source_part_of_speech": state.source_part_of_speech,
        "target_part_of_speech": state.target_part_of_speech,
    }

    # Execute with quality gate
    result = await execute_with_quality_gate(
        state, get_examples, "examples", TaskType.EXAMPLES, inputs
    )

    logger.debug(
        "examples_result",
        word=state.source_word,
        examples=result.get("examples", []),
        quality_approved=result.get("examples_quality_approved", False),
        quality_score=result.get("examples_quality_score", 0.0),
    )

    return {
        "examples": result.get("examples", []),
        "examples_quality_approved": result.get("examples_quality_approved", False),
        "examples_quality_score": result.get("examples_quality_score", 0.0),
    }


async def node_get_conjugation(state: VocabState) -> VocabState:
    """Get verb conjugation if applicable."""
    if state.target_part_of_speech != "verb":
        return {
            "conjugation": None,
            "conjugation_quality_approved": True,
            "conjugation_quality_score": 10.0,
        }

    inputs = {
        "target_word": state.target_word,
        "target_language": state.target_language,
        "target_part_of_speech": state.target_part_of_speech,
    }

    # Execute with quality gate
    result = await execute_with_quality_gate(
        state, get_conjugation, "conjugation", TaskType.CONJUGATION, inputs
    )

    logger.debug(
        "conjugation_result",
        word=state.target_word,
        conjugation=result.get("conjugation", None),
        quality_approved=result.get("conjugation_quality_approved", False),
        quality_score=result.get("conjugation_quality_score", 0.0),
    )

    return {
        "conjugation": result.get("conjugation", None),
        "conjugation_quality_approved": result.get(
            "conjugation_quality_approved", False
        ),
        "conjugation_quality_score": result.get("conjugation_quality_score", 0.0),
    }


# Supervisor nodes for quality gates
async def supervisor_check_sequential_quality(state: VocabState) -> VocabState:
    """Check if sequential steps (validation, classification, translation) passed quality gates."""

    # Check quality gates for sequential steps
    quality_checks = [
        ("validation", state.validation_quality_approved),
        ("classification", state.classification_quality_approved),
        ("translation", state.translation_quality_approved),
    ]

    all_passed = True
    failed_steps = []

    for step_name, quality_approved in quality_checks:
        if not quality_approved:
            all_passed = False
            failed_steps.append(step_name)

    if all_passed:
        logger.info(
            "sequential_quality_gates_passed", status="Ready for parallel execution"
        )
        return {"sequential_quality_passed": True}
    else:
        logger.warning("sequential_quality_gates_failed", failed_steps=failed_steps)
        return {
            "sequential_quality_passed": False,
            "failed_quality_steps": failed_steps,
        }


async def supervisor_coordinate_parallel_tasks(state: VocabState) -> VocabState:
    """Supervisor coordinates and validates parallel task execution."""

    # Determine which parallel tasks should be executed
    parallel_tasks = await supervisor.coordinate_parallel_tasks(state)

    logger.info("parallel_tasks_coordination", tasks=parallel_tasks)

    return {"parallel_tasks_to_execute": parallel_tasks}


async def supervisor_final_quality_check(state: VocabState) -> VocabState:
    """Final quality check before completing the vocabulary processing."""

    # Check all quality gates
    quality_fields = [
        "validation_quality_approved",
        "classification_quality_approved",
        "translation_quality_approved",
        "media_quality_approved",
        "examples_quality_approved",
        "synonyms_quality_approved",
        "syllables_quality_approved",
        "conjugation_quality_approved",
    ]

    quality_scores = []
    failed_quality_checks = []

    for field in quality_fields:
        approved = getattr(state, field, False)
        score_field = field.replace("_approved", "_score")
        score = getattr(state, score_field, 0.0)

        if approved:
            quality_scores.append(score)
        else:
            failed_quality_checks.append(field.replace("_quality_approved", ""))

    # Calculate overall quality score
    overall_quality = (
        sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
    )

    logger.info(
        "final_quality_assessment",
        overall_quality=overall_quality,
        passed_checks=len(quality_scores),
        failed_checks=len(failed_quality_checks),
        failed_quality_checks=failed_quality_checks,
    )

    return {
        "overall_quality_score": overall_quality,
        "quality_checks_passed": len(quality_scores),
        "quality_checks_failed": len(failed_quality_checks),
        "processing_complete": True,
    }


async def join_parallel_tasks(state: VocabState) -> VocabState:
    """Join node that tracks completed parallel tasks and triggers final quality check when all are done."""

    # Get the list of completed tasks from state (initialize if not exists or None)
    completed_tasks = getattr(state, "completed_parallel_tasks", []) or []

    # Determine which task just completed by checking which quality fields are set
    parallel_tasks = ["media", "examples", "synonyms", "syllables"]

    # Add conjugation if it's a verb
    if getattr(state, "target_part_of_speech", None) == "verb":
        parallel_tasks.append("conjugation")

    # Add pronunciation (no quality gate needed)
    parallel_tasks.append("pronunciation")

    # Find newly completed tasks (tasks that have quality approval but aren't in completed list)
    newly_completed = []
    for task in parallel_tasks:
        if task == "pronunciation":
            # Pronunciation is complete if it has pronunciations data (no quality gate)
            if hasattr(state, "pronunciations") and state.pronunciations is not None:
                if task not in completed_tasks:
                    newly_completed.append(task)
        else:
            # Other tasks need quality approval
            quality_field = f"{task}_quality_approved"
            if (
                hasattr(state, quality_field)
                and getattr(state, quality_field, None) is not None
                and task not in completed_tasks
            ):
                newly_completed.append(task)

    # Add newly completed tasks to the list
    updated_completed_tasks = list(set(completed_tasks + newly_completed))

    # Log the current state
    logger.info(
        "join_parallel_tasks",
        newly_completed=newly_completed,
        total_completed=len(updated_completed_tasks),
        expected_total=len(parallel_tasks),
        completed_tasks=updated_completed_tasks,
        expected_tasks=parallel_tasks,
    )

    # Check if all expected parallel tasks are complete
    all_complete = set(updated_completed_tasks) >= set(parallel_tasks)

    if all_complete:
        logger.info(
            "join_parallel_tasks",
            status="All parallel tasks complete, proceeding to final quality check",
        )
        return {
            "completed_parallel_tasks": updated_completed_tasks,
            "parallel_tasks_complete": True,
        }
    else:
        logger.info(
            "join_parallel_tasks", status="Waiting for more parallel tasks to complete"
        )
        return {
            "completed_parallel_tasks": updated_completed_tasks,
            "parallel_tasks_complete": False,
        }
