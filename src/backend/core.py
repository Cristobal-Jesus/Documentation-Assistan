import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain.agents import create_agent # type: ignore
from langchain.chat_models import init_chat_model
from langchain.messages import ToolMessage
from langchain.tools import tool
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# Initialize embeddings (same as ingestion.py)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Initialize vector store
vectorestore = PineconeVectorStore(
    index_name="langchain-doc-index",
    embedding=embeddings,
)

# Initialize chat model
model = init_chat_model("gpt-5.2", model_provider="openai")


@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """Retrieve revelant documentation to help answer user queries about LangChain."""
    # Retrieve top 4 most similar documents
    retrieve_docs = vectorestore.as_retriever().invoke(query, k=4)
    
    # Serialize documents for the model
    serialized = "\n\n".join(
        (f"Source: {doc.metadata.get('source', 'Unknown')}\n\nContent: {doc.page_content}") # type: ignore
        for doc in retrieve_docs
    )
    
    # Return both serialized content and raw documents
    return serialized, retrieve_docs
    


def run_llm(query: str) -> Dict[str, Any]: # type: ignore
    """
    Run the RAG pipeline to answer a query using retrieved documentation.

    Args:
        query (str): The user's question

    Returns:
        Dict[str, Any]: 
            - answer: The generated answer
            - context: List of retrieved documents
    """
    
    # Create the agent with retrieval tool
    system_prompt = (
        "You are a helpful AI assistant that answers questions about LangChain documentation. "
        "You have access to a tool that retrieves relevant documentation. "
        "Use the tool to find relevant information before answering questions. "
        "Always cite the sources you use in your answers. "
        "If you cannot find the answer in the retrieved documentation, say so."
    )
    
    agent = create_agent(model, tools=[retrieve_context], system_prompt=system_prompt) # type: ignore
    
    # Build messages list
    messages = [{"role": "user", "content": query}]
    
    # Invoke the agent
    response = agent.invoke({"messages": messages}) # type: ignore
    
    # Extract the answer from the last AI message
    answer = response["messages"][-1].content
    
    # Extract context documents from ToolMessage artifacts
    context_docs = []
    for message in response["messages"]:
        # Check if this is a ToolMessage with artifact
        if isinstance(message, ToolMessage) and hasattr(message, "artifact"):
            # The artifact should contain the list of Document objects
            if isinstance(message.artifact, list):
                context_docs.extend(message.artifact) # type: ignore
    
    return {
        "answer": answer,
        "context": context_docs
    }

if __name__ == '__main__':
    result = run_llm(query="what are deep agents?")
    print(result)
    