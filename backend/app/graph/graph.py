from backend.app.utils import logging
import logging
from langgraph.graph import StateGraph, END, START


from app.graph.state import AgentState
from app.graph.nodes import (
    planner_node,
    executor_node,
    critic_node,
    guardrail_node,
    output_node
)


logger = logging.getLogger(__name__)


def route_after_critic(state: AgentState) -> str:
    """Conditional edge - self-correction.

    Decides:
    - If PASS --> proceed to guardrail
    - If REVISE and attempts < 3 --> loop back to executor
    - if REVISE and attempts >=3 --> force proceed to guardrail
    """

    verdict = state.get("critic_verdict", "PASS")
    attempt = state.get("attempt_number", 1)
    max_attempts = 3 

    logger.info(f"Router: verdict={verdict}, attempt={attempt}")


    if verdict == "PASS":
        logger.info("PASS --> proceeding to guardrail")
        return "guardrail"


    if attempt < max_attempts:
        logger.info(f"{verdict} Loop back to the executor (attempts: {attempt}/{max_attempts})")
        return "executor"


    logger.info(f"Max attempts reached --> forcing to guardrail")
    return "guardrail"


def build_graph():
    """
    Build and compile the LangGraph with self-correction loop.

    FLOW:
    START --> planner --> executor --> critic --> [conditional]
                                                       |__PASS --> guardrail --> output --> END
                                                       |__REVISE --> executor (loop back)
    """

    graph = StateGraph(AgentState)

    # ADDING NODES 
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("critic", critic_node)
    graph.add_node("guardrail", guardrail_node)
    graph.add_node("output", output_node)

    # ADDING EDGES
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "critic")
    graph.add_edge("guardrail", "output")
    graph.add_edge("output", END)


    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "executor": "executor",
            "guardrail": "guardrail"
        }
    )

    compiled_graph = graph.compile()

    logger.info("LangGraph compiled with self-correction loop")

    return compiled_graph



def run_graph(initial_state: AgentState) -> AgentState:
    """
    Run the graph with initial state and return final state.
    """
    graph = build_graph()
    logger.info("Running graph")

    final_state = graph.invoke(initial_state)
    logger.info(f"Graph execution complete. Attempts: {final_state.get("attempt_number", 1) - 1}, Score: {final_state.get("critic_score", 0)} ")
    return final_state

    