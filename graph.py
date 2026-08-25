from typing import TypedDict
from agents import ask_research_agent, run_prep_agent
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




async def agent_node(state: State):
    debug_print("Agent started")

    question = state["user_question"]

    result = await ask_research_agent(question)

    debug_print("Agent finished")

    parsed = result["structured_response"]

    return {
        "interactions": parsed.interactions,
        "research_notes": parsed.research_notes,
    }


async def prep_node(state: State):
    debug_print("Prep agent started")

    final_answer = await run_prep_agent(state)

    debug_print("Prep agent finished")

    return {"final_answer": final_answer}


graph = StateGraph(State)

graph.add_node("agent", agent_node)
graph.add_node("prep", prep_node)

graph.add_edge(START, "agent")
graph.add_edge("agent", "prep")
graph.add_edge("prep", END)

checkpointer = InMemorySaver()

app = graph.compile(checkpointer=checkpointer)

debug_print("Graph compiled successfully.")

async def Pipeline(query):
    config = {"configurable": {"thread_id": "session_1"}}

    initial_state = {
        "session_id": "session_1",
        "user_question": query,
        "interactions": [],
        "research_notes": [],
        "final_answer": "",
        "evaluation": None
    }

    result = await app.ainvoke(initial_state,config=config)

    # Check whether the graph is paused at an interrupt
    while True:
        state = app.get_state(config)
        if not state.interrupts:
            break
        interrupt_data = state.interrupts[0].value

        if interrupt_data["type"] == "user_question":

            question = interrupt_data["question"]

            print("\nAgent:")
            print(question)

            user_answer = input("\nYou: ")

            result = await app.ainvoke(Command(resume=user_answer),config=config)

    pprint(result)

    print("\n\n\n\n"+"="*20+"Extra warning to be dealt with later"+"="*20)


if __name__ == "__main__":
    import asyncio
    query = "What internships has vinayak done?"
    asyncio.run(Pipeline(query))