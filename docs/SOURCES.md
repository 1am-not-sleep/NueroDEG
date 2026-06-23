# Sources and Reference Workflows

These sources informed the upgraded project structure.

## Agent Architecture

- OpenAI Agents SDK documentation: https://openai.github.io/openai-agents-python/
  - Used as a reference for tools, guardrails, tracing, and agent sessions.

- OpenAI Agents SDK tools documentation: https://openai.github.io/openai-agents-python/tools/
  - Used as a reference for treating each analysis function as a callable tool.

- OpenAI Agents SDK guardrails documentation: https://openai.github.io/openai-agents-python/guardrails/
  - Used as a reference for separating validation/safety checks from the main tool flow.

- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
  - Used as a reference for stateful workflows, durable execution, and human-in-the-loop agent design.

- LangGraph thinking guide: https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph
  - Used as a reference for modeling agent workflows as nodes, state, and transitions.

- ReAct paper: https://arxiv.org/abs/2210.03629
  - Used as a conceptual reference for alternating action/tool use with observations.

## Interface

- Streamlit chat app tutorial: https://docs.streamlit.io/develop/tutorials/chat-and-llm-apps/build-conversational-apps
  - Used as a reference for adding `st.chat_message` and `st.chat_input`.

- Streamlit app testing: https://docs.streamlit.io/develop/api-reference/app-testing
  - Used as a reference for `streamlit.testing.v1.AppTest`.

## Bioinformatics

- GSEApy introduction: https://gseapy.readthedocs.io/en/latest/introduction.html
  - Used as a future reference for adding GO/KEGG and Enrichr-based enrichment.

- Allen Brain Map cell types RNA-seq data: https://brain-map.org/our-research/cell-types-taxonomies/cell-types-database-rna-seq-data
  - Used as a future reference for brain cell-type expression resources.
