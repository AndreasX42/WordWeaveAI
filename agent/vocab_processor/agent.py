from langgraph.graph import END, StateGraph

from vocab_processor.utils import *
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


def build_vocab_graph():
    """Build the optimized vocabulary processing graph with proper dependencies."""
    workflow = StateGraph(VocabState)

    # Add all processing nodes
    workflow.add_node("validate_source_word", node_validate_source_word)
    workflow.add_node("get_classification", node_get_classification)
    workflow.add_node("get_translation", node_get_translation)
    workflow.add_node("get_syllables", node_get_syllables)

    # Nodes that can run immediately after translation (no syllables needed)
    workflow.add_node("get_media", node_get_media)
    workflow.add_node("get_examples", node_get_examples)
    workflow.add_node("get_synonyms", node_get_synonyms)
    workflow.add_node("get_conjugation", node_get_conjugation)

    # Node that needs syllables
    workflow.add_node("get_pronunciation", node_get_pronunciation)

    # Define graph structure
    workflow.set_entry_point("validate_source_word")

    # Add conditional edge from validation
    workflow.add_conditional_edges(
        "validate_source_word",
        should_proceed_after_validation,
        {"get_classification": "get_classification", END: END},
    )

    workflow.add_edge("get_classification", "get_translation")

    # CORRECTED: Split into two parallel groups
    # Group 1: Can start immediately after translation (4 parallel tasks)
    workflow.add_edge("get_translation", "get_media")
    workflow.add_edge("get_translation", "get_examples")
    workflow.add_edge("get_translation", "get_synonyms")
    workflow.add_edge("get_translation", "get_conjugation")

    # Group 2: Syllables must complete first, then pronunciation
    workflow.add_edge("get_translation", "get_syllables")
    workflow.add_edge("get_syllables", "get_pronunciation")

    # All nodes end the workflow
    workflow.add_edge("get_media", END)
    workflow.add_edge("get_examples", END)
    workflow.add_edge("get_synonyms", END)
    workflow.add_edge("get_conjugation", END)
    workflow.add_edge("get_pronunciation", END)

    return workflow.compile()


# Create the graph instance
graph = build_vocab_graph()
