from langchain.tools.retriever import create_retriever_tool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.chat_message_histories.upstash_redis import UpstashRedisChatMessageHistory

from google.cloud import storage

import os
import yaml

cfg = yaml.safe_load(open("secrets/secrets.yaml", "r"))

# API keys
os.environ["LANGCHAIN_API_KEY"] = cfg["LANGCHAIN_API_KEY"]
os.environ["OPENAI_API_KEY"] = cfg["OPENAI_API_KEY"]
os.environ["TAVILY_API_KEY"] = cfg["TAVILY_API_KEY"]
os.environ["ALLOW_RESET"] = "True"

# Google auth
storage_client = storage.Client.from_service_account_json("secrets/profound-saga-420500-b3f6a7d4835f.json")

# Constants
BUCKET_NAME = "study-app-test"
CHROMA_PERSIST = "chroma_db"
AGENT_EXEC = "agent_executor"


def remove_temp_bucket(temp_bucket):
    buckets = storage_client.list_buckets()
    buckets = [bucket.name for bucket in buckets]
    if temp_bucket in buckets:
        b = storage_client.get_bucket(temp_bucket)
        blobs = b.list_blobs()
        for blob in blobs:
            blob.delete()
        b.delete()


def upload_user_files_to_google_cloud(filepaths, user_bucket=BUCKET_NAME):
    # Get blobs from bucket; create the bucket if it doesn't exist
    buckets = storage_client.list_buckets()
    buckets = [bucket.name for bucket in buckets]
    if user_bucket not in buckets:
        bucket = storage_client.create_bucket(user_bucket)
    else:
        bucket = storage_client.get_bucket(user_bucket)

    blobs = bucket.list_blobs()
    blob_names = [blob.name for blob in blobs]

    # Upload files to Google Cloud
    for fp in filepaths:
        fname = os.path.basename(fp)

        # If a file already exists in the user bucket, skip (no duplicates)
        if fname in blob_names:
            continue

        # Upload the file to Google Cloud
        file_blob = bucket.blob(fname)
        file_blob.upload_from_filename(fp)


async def get_agent_executor_and_respond(query, user_bucket=BUCKET_NAME):
    # If user bucket has a vector db, create a retriever. Otherwise, don't.
    buckets = storage_client.list_buckets()
    buckets = [bucket.name for bucket in buckets]
    pages = []

    # If user bucket not in cloud storage, create the bucket
    if user_bucket not in buckets:
        storage_client.create_bucket(user_bucket)
    else:
        bucket = storage_client.get_bucket(user_bucket)
        blobs = bucket.list_blobs()

        # Load files from blobs into vector store
        for blob in blobs:
            blob.download_to_filename(blob.name)

            # Document loader (just PDFs for now)
            loader = PyPDFLoader(blob.name)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=200,
                chunk_overlap=20
            )
            pages.extend(loader.load_and_split(text_splitter))

            # Delete local file
            os.remove(blob.name)

    # If no files were uploaded, leave retriever as None
    if len(pages) == 0:
        retriever = None
    else:
        vector_db = Chroma.from_documents(pages, embedding=OpenAIEmbeddings())
        retriever = vector_db.as_retriever(search_kwargs={"k": 3})

    # Model
    llm = ChatOpenAI(model="gpt-3.5-turbo-1106", temperature=0.7, streaming=True)

    # Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a friendly AI assistant. Based on the given retriever/search tools and chat history,
        answer the user's queries."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    # Tools
    search = TavilySearchResults()
    tools = [search]

    # Add retriever tool (if applicable)
    if retriever:
        retriever_tool = create_retriever_tool(retriever, "upload-file-search",
                                               """This tool should be your first resort when searching for information 
                                               to answer a user's query. If no information can be found using this tool,
                                               use Tavily search.""")
        tools = [retriever_tool, search]

    # Upstash Redis chat persistence
    ttl = 60 if "temp" in user_bucket else -1
    history = UpstashRedisChatMessageHistory(
        url=cfg["UPSTASH_URL"],
        token=cfg["UPSTASH_TOKEN"],
        session_id=user_bucket,
        ttl=ttl
    )

    # Memory (include Redis history)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, chat_memory=history)

    # Agent and executor
    agent = create_openai_functions_agent(llm=llm, prompt=prompt, tools=tools)
    agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory)

    # Invoke to get response
    response = await agent_executor.ainvoke({"input": query})

    return response["output"]


if __name__ == "__main__":
    pass
