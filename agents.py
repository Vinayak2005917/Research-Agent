from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from openai import OpenAI
from openai import AsyncOpenAI
from tools import Get_relevant_webpages, batch_read_pages
from dotenv import load_dotenv
from vector_DB import retrieve_top_k
from langchain.tools import tool
from langgraph.types import interrupt
from pydantic import BaseModel, Field
import os
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")

Smart_model = ChatOpenAI(
    model="openai/gpt-5.6-luna",
    api_key=api_key,
    base_url="https://api.aicredits.in/v1",
)



class ResearchOutput(BaseModel):
    interactions: list[dict] = Field(default_factory=list)
    research_notes: list[dict] = Field(default_factory=list)


@tool("ask_user",description="Ask the user a question and get their response.")
async def ask_user(question: str) -> str:
    answer = interrupt({
        "type": "user_question",
        "question": question
    })

    return answer


main_agent_system_prompt = """
You are a research agent. You have been given a question to research along with documents which have already been chuncked
and embedded into a vector database. You job is to collect facts and their souces and provide them in a structured format for the next agent.

## Tools:
1. retrieve_top_k: This tool allows you to retrieve the top k relevant documents from the vector database based on a query.
2. Get_relevant_webpages: This tool allows you to retrieve relevant webpages based on a query.
3. batch_read_pages: This tool allows you to read the content of multiple webpages at once.
4. ask_user: This tool allows you to ask the user a question and get their response.

## Priority of tools:
* Always start with retrieve_top_k tool to check your vector database.
* Recommendation : Try multiple queries with a single word or two, with a k between 3 to 7.
* Only use Get_relevant_webpages and batch_read_pages as a fallback.
* Use the ask_user tool only when you are stuck and need clarification from the user (eg. If to use the web tools or not.)

## Important:
* DO NOT MAKE UP ANY INFORMATION OR SOURCES. If you cannot find the answer, say "I don't know".
* DO NOT USE MARKDOWN OR HTML IN YOUR ANSWERS. Provide plain text answers only.
* Answer in a few lines, preferably less than 5 lines.

* For now, ALWAYS ASK THE USER BEFORE USING THE WEB TOOLS.

## State Feilds:
* session id: A unique identifier for the current user, use this for the retrieve_top_k tool.
* user_question: The question that the user has asked you to research.
* Interactions: A list of interactions between you and the user, each interaction contains a question and an answer.
* research_notes: A list of facts that you have found during your research, each fact contains the fact and the list of all sources of the fact.
```
Schema:
{
    "interactions": [
        {
            "question": "What is the question you are trying to answer?",
            "answer": "The answer to the question."
        }
    ]
}
``` 

"""

research_agent = create_agent(
    model=Smart_model,
    tools=[Get_relevant_webpages, batch_read_pages, retrieve_top_k, ask_user],
    system_prompt=main_agent_system_prompt,
    response_format=ResearchOutput
)

async def ask_research_agent(question):
    result = await research_agent.ainvoke({
        "messages": [
            {"role": "user", "content": question}
        ]
    })

    return result





class PrepOutput(BaseModel):
    final_answer: str = ""


prep_agent_system_prompt = """
You are a synthesis agent. You will be given the full research state, including the user's question,
interactions with the user, and research notes (facts with sources).

Your job is to write a final answer to the user's question based ONLY on the research notes.

## Important:
* Use only the facts in the research notes. DO NOT MAKE UP ANY INFORMATION OR SOURCES.
* Cite the sources for each claim.
* If the information is insufficient, say so honestly.
* Your final answer MUST be in Markdown format.
"""


prep_agent = create_agent(
    model=Smart_model,
    system_prompt=prep_agent_system_prompt,
    response_format=PrepOutput
)


# Takes the entire state and produces only the final answer
async def run_prep_agent(state: dict) -> str:
    state_context = f"""
        User question:
        {state.get("user_question", "")}

        Interactions with the user:
        {state.get("interactions", [])}

        Research notes (facts and their sources):
        {state.get("research_notes", [])}
    """

    result = await prep_agent.ainvoke({
        "messages": [
            {"role": "user", "content": state_context}
        ]
    })

    return result["structured_response"].final_answer
