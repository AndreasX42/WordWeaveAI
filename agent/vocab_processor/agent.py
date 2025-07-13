from langgraph.graph import END, StateGraph

from vocab_processor.utils.nodes import (
    join_parallel_tasks,
    node_get_classification,
    node_get_conjugation,
    node_get_examples,
    node_get_media,
    node_get_pronunciation,
    node_get_syllables,
    node_get_synonyms,
    node_get_translation,
    node_validate_source_word,
    supervisor_check_sequential_quality,
    supervisor_coordinate_parallel_tasks,
    supervisor_final_quality_check,
)
from vocab_processor.utils.state import VocabState


# Conditional function to decide path after validation
def should_proceed_after_validation(state: VocabState) -> str:
    """
    Determines the next step based on word validation.
    If valid, proceeds to classification. Otherwise, ends the graph.
    """
    if state.validation_passed is True:
        return "get_classification"
    else:
        return END


# Conditional function to decide path after classification
def should_proceed_after_classification(state: VocabState) -> str:
    """
    Determines the next step based on classification and existence check.
    If word doesn't exist, proceeds to translation. Otherwise, ends the graph.
    """
    if state.word_exists is True:
        return END
    else:
        return "get_translation"


# Conditional function to decide path after sequential quality check
def should_proceed_to_parallel_tasks(state: VocabState) -> str:
    """
    Determines whether to proceed to parallel tasks based on quality check.
    If quality checks passed, proceeds to parallel tasks. Otherwise, ends the graph.
    """
    if state.sequential_quality_passed is True:
        return "supervisor_coordinate_parallel_tasks"
    else:
        return END


# Conditional function to decide when to proceed to final quality check
def should_proceed_to_final_quality_check(state: VocabState) -> str:
    """
    Determines whether to proceed to final quality check based on task completion.
    If all tasks are complete, proceeds to final quality check. Otherwise, continues join loop.
    """
    if state.parallel_tasks_complete is True:
        return "supervisor_final_quality_check"
    else:
        return END


def build_vocab_graph():
    """Build the supervisor-enhanced vocabulary processing graph with quality gates."""
    workflow = StateGraph(VocabState)

    # Add sequential processing nodes with quality gates
    workflow.add_node("validate_source_word", node_validate_source_word)
    workflow.add_node("get_classification", node_get_classification)
    workflow.add_node("get_translation", node_get_translation)

    # Add supervisor nodes
    workflow.add_node(
        "supervisor_check_sequential_quality", supervisor_check_sequential_quality
    )
    workflow.add_node(
        "supervisor_coordinate_parallel_tasks", supervisor_coordinate_parallel_tasks
    )
    workflow.add_node("join_parallel_tasks", join_parallel_tasks)
    workflow.add_node("supervisor_final_quality_check", supervisor_final_quality_check)

    # Add parallel processing nodes
    workflow.add_node("get_media", node_get_media)
    workflow.add_node("get_examples", node_get_examples)
    workflow.add_node("get_synonyms", node_get_synonyms)
    workflow.add_node("get_conjugation", node_get_conjugation)
    workflow.add_node("get_syllables", node_get_syllables)
    workflow.add_node("get_pronunciation", node_get_pronunciation)

    # Define graph structure
    workflow.set_entry_point("validate_source_word")

    # Sequential processing with quality gates
    workflow.add_conditional_edges(
        "validate_source_word",
        should_proceed_after_validation,
        {"get_classification": "get_classification", END: END},
    )

    # Add conditional edge after classification to check existence
    workflow.add_conditional_edges(
        "get_classification",
        should_proceed_after_classification,
        {"get_translation": "get_translation", END: END},
    )

    workflow.add_edge("get_translation", "supervisor_check_sequential_quality")

    # Conditional edge based on sequential quality check
    workflow.add_conditional_edges(
        "supervisor_check_sequential_quality",
        should_proceed_to_parallel_tasks,
        {
            "supervisor_coordinate_parallel_tasks": "supervisor_coordinate_parallel_tasks",
            END: END,
        },
    )

    # Parallel task execution
    workflow.add_edge("supervisor_coordinate_parallel_tasks", "get_media")
    workflow.add_edge("supervisor_coordinate_parallel_tasks", "get_examples")
    workflow.add_edge("supervisor_coordinate_parallel_tasks", "get_synonyms")
    workflow.add_edge("supervisor_coordinate_parallel_tasks", "get_conjugation")
    workflow.add_edge("supervisor_coordinate_parallel_tasks", "get_syllables")

    # Pronunciation depends on syllables
    workflow.add_edge("get_syllables", "get_pronunciation")

    # All parallel tasks feed into join node that tracks completion
    workflow.add_edge("get_media", "join_parallel_tasks")
    workflow.add_edge("get_examples", "join_parallel_tasks")
    workflow.add_edge("get_synonyms", "join_parallel_tasks")
    workflow.add_edge("get_conjugation", "join_parallel_tasks")
    workflow.add_edge("get_pronunciation", "join_parallel_tasks")

    # Join node conditionally proceeds to final quality check only when all tasks complete
    workflow.add_conditional_edges(
        "join_parallel_tasks",
        should_proceed_to_final_quality_check,
        {
            "supervisor_final_quality_check": "supervisor_final_quality_check",
            END: END,
        },
    )

    # Final quality check ends the workflow
    workflow.add_edge("supervisor_final_quality_check", END)

    return workflow.compile()


# Create the graph instance
graph = build_vocab_graph()
