import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents import sql_analyst
from utils.llm_pick import pick_llm
from utils.etl_tools import ETLTools
from Models.schema import RouterSchema, DataAgentSchema
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst


llm = pick_llm("low")

llm_router = llm.with_structured_output(
    RouterSchema,
    method="json_mode"
)


# ---------------------------- DATA AGENT GRAPH ---------------------------- #



def router_node(state: DataAgentSchema):
    message = state.messages[-1].content

    route_prompt = f"""
You are a router for a data agent.

Choose exactly one route:
- sql: querying, counting, filtering, or analyzing existing PostgreSQL data.
- etl: extracting data from an API or file, transforming it, or loading it.

Return JSON containing both required fields:
{{
    "answer": "etl",
    "comments": "The request extracts data from an API."
}}

For SQL requests, set answer to "sql".
For ETL requests, set answer to "etl".
Explain the reason in comments.

User request: {message}
"""

    route_response_dict = llm_router.invoke(route_prompt).model_dump()
    route_response = route_response_dict["answer"].strip().lower()

    if route_response not in ("sql", "etl"):
        raise ValueError(f"Invalid route returned by LLM: {route_response}")

    state.route_response = route_response
    return state

    
# route_prompt = f"""
#     You are a router for a data agent.

#     Choose exactly one route:
#     - sql: querying, counting, filtering, or analyzing existing PostgreSQL data.
#     - etl: extracting data from an API or file, transforming it, or loading it.

#     Return JSON containing both required fields:
#     {{
#     "answer": "etl",
#     "comments": "The request extracts data from an API."
#     }}

#     For SQL requests, set answer to "sql" and explain why in comments.
#     For ETL requests, set answer to "etl" and explain why in comments.

#     User request: {message}
# """

#     route_response_dict = llm_router.invoke(route_prompt).model_dump()

#     route_response = route_response_dict["answer"].strip().lower()

#     if route_response not in ("sql", "etl"):
#         raise ValueError(f"Invalid route returned by LLM: {route_response}")

#     state.route_response = route_response
#     return state



def etl_node(state: DataAgentSchema):
    message = state.messages[-1].content

    response = etl_analyst.invoke({
        "messages": [HumanMessage(content=message)]
    })

    # Find the final assistant message from ETL agent
    messages = response.get("messages", [])
    final_answer = ""

    for item in reversed(messages):
        if (
            getattr(item, "type", "") == "ai"
            and isinstance(getattr(item, "content", ""), str)
            and item.content.strip()
            and not getattr(item, "tool_calls", None)
        ):
            final_answer = item.content
            break

    if not final_answer:
        final_answer = "ETL operation completed, but no final text response was returned."

    state.messages = state.messages + [
        AIMessage(content=final_answer)
    ]

    return state


def sql_node(state: DataAgentSchema):
    message = state.messages[-1].content

    input_schema = {
        "messages": [],
        "user_question": message,
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }

    response = sql_analyst.invoke(input_schema)

    # Extract the actual final answer from SQL agent
    final_answer = response.get("final_answer", "")

    if not final_answer:
        final_answer = "SQL agent did not return a final answer."

    # Append a normal AI message instead of the entire dictionary
    state.messages = state.messages + [
        AIMessage(content=final_answer)
    ]

    return state




data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")

def route_edge(state: DataAgentSchema) -> str:
    if state.route_response == "sql":
        return "sql_node"
    elif state.route_response == "etl":
        return "etl_node"
    else:
        raise ValueError(f"Invalid route response: {state.route_response}")


data_agent_graph.add_conditional_edges("router_node", route_edge,
                                      {
                                          "sql_node": "sql_node",
                                          "etl_node": "etl_node"
                                      })

data_agent = data_agent_graph.compile()

# Optional|
from IPython.display import display, Image
img = Image(data_agent.get_graph().draw_mermaid_png())
with open("data_agent_graph.png", "wb") as f:
    f.write(img.data)



if __name__ == "__main__":

    response = data_agent.invoke(
        {"messages":[HumanMessage(content="I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in the csv folder")],
         "route_response": ""}
    )

    print(response)




