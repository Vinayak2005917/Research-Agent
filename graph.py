from typing import TypedDict
from agents import ask_research_agent, run_prep_agent, run_fact_check_agent
from langgraph.graph import StateGraph, START, END
from utils import debug_print
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver
from pprint import pprint

class Interations(TypedDict):
    question: str
    answer: str

class Facts(TypedDict):
    fact : str
    source : list[str]

class State(TypedDict):
    session_id: str
    user_question: str

    interactions: list[Interations]

    research_notes: list[Facts]
    final_answer: str

    evaluation: dict | None




async def research_agent_node(state: State):
    debug_print(f"Research agent started with session id {state['session_id']} and question: {state['user_question']}")

    question = state["user_question"]

    result = await ask_research_agent(question)

    parsed = result["structured_response"]

    debug_print(f"Research agent finished with {len(parsed.interactions)} no. of interactions and {len(parsed.research_notes)} no. of research notes")
    debug_print(f"interactions: {parsed.interactions}")
    debug_print(f"research_notes: {parsed.research_notes}")

    return {
        "interactions": parsed.interactions,
        "research_notes": parsed.research_notes,
    }


async def prep_agent_node(state: State):
    debug_print(f"Prep agent started with session id {state['session_id']} and question: {state['user_question']}")

    final_answer = await run_prep_agent(state)

    debug_print(f"Prep agent finished with final answer: {len(final_answer)} characters")

    return {"final_answer": final_answer}


async def fact_check_node(state: State):
    debug_print(f"Fact-check agent started for session id {state['session_id']}")

    result = await run_fact_check_agent(state)

    debug_print(f"Fact-check agent finished with {len(result['evaluation']['corrections'])} corrections")

    return result


graph = StateGraph(State)

graph.add_node("agent", research_agent_node)
graph.add_node("prep", prep_agent_node)
graph.add_node("fact_check", fact_check_node)

graph.add_edge(START, "agent")
graph.add_edge("agent", "prep")
graph.add_edge("prep", "fact_check")
graph.add_edge("fact_check", END)

checkpointer = InMemorySaver()

app = graph.compile(checkpointer=checkpointer)

debug_print("Graph compiled successfully.")

async def run_pipeline(query: str, session_id: str, ask_user) -> str:
    config = {"configurable": {"thread_id": session_id}}

    initial_state = {
        "session_id": session_id,
        "user_question": query,
        "interactions": [],
        "research_notes": [],
        "final_answer": "",
        "evaluation": None,
    }

    await app.ainvoke(initial_state, config=config)

    # Resume the graph whenever it is paused at an interrupt
    while True:
        state = app.get_state(config)
        if not state.interrupts:
            break
        interrupt_data = state.interrupts[0].value

        if interrupt_data["type"] == "user_question":
            user_answer = await ask_user(interrupt_data["question"])
            await app.ainvoke(Command(resume=user_answer), config=config)
            debug_print(f"Resumed graph with user answer: {user_answer}")

    final_state = app.get_state(config)
    return final_state.values.get("final_answer", "")


if __name__ == "__main__":
    import asyncio

    async def cli_ask(question: str) -> str:
        print("\nAgent:")
        print(question)
        return input("\nYou: ")

    query = "What internships has vinayak done?"
    answer = asyncio.run(run_pipeline(query, "session_1", cli_ask))
    print("\nFinal answer:\n")
    print(answer)