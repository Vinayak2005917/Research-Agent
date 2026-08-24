from typing import TypedDict
from agent import ask_main_agent
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI


class State(TypedDict):
    question: str
    answer: str


def agent(state: State):
    response = ask_main_agent(State["question"])
    return {"answer": response}


#Graph
graph = StateGraph(State)

graph.add_node("agent", agent)

graph.add_edge(START, "agent")
graph.add_edge("agent", END)

app = graph.compile()

result = app.invoke({
    "question": "What is quantum computing?",
    "answer": ""
})

print(result["answer"])