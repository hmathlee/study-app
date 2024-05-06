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

import MySQLdb as mdb
from google.cloud import storage

import os
import yaml
from pathlib import Path

cfg = yaml.safe_load(open("secrets/secrets.yaml", "r"))

# API keys
os.environ["LANGCHAIN_API_KEY"] = cfg["LANGCHAIN_API_KEY"]
os.environ["OPENAI_API_KEY"] = cfg["OPENAI_API_KEY"]
os.environ["TAVILY_API_KEY"] = cfg["TAVILY_API_KEY"]
os.environ["ALLOW_RESET"] = "True"

# Google auth
storage_client = storage.Client.from_service_account_json("secrets/profound-saga-420500-0e972a75285b.json")

# Constants
BUCKET_NAME = "study-app-test"
CHROMA_PERSIST = "chroma_db"
AGENT_EXEC = "agent_executor"


def mysql_register_user(email, username, password):
    conn = mdb.connect(cfg["MYSQL_SERVER"], cfg["MYSQL_USERNAME"], cfg["MYSQL_PASSWORD"], "study-app-users")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_credentials (email, username, password) VALUES (%s, %s, %s)",
                   (email, username, password))
    conn.commit()
    conn.close()


def upload_chroma_db(bucket):
    if os.path.exists(CHROMA_PERSIST):
        db_files = get_all_path_strs(CHROMA_PERSIST)
        for f in db_files:
            blob = bucket.blob(f)
            blob.upload_from_filename(f)


def get_all_path_strs(root):
    res = []
    for path, subdirs, files in os.walk(root):
        for name in files:
            res.append(os.path.join(path, name))
    return res


def upload_user_files_and_db_to_google_cloud(filepaths, user_bucket=BUCKET_NAME):
    # Get blobs from bucket
    bucket = storage_client.get_bucket(user_bucket)
    blobs = bucket.list_blobs()
    blob_names = [blob.name for blob in blobs]

    # Blob containing the vector database
    db_blob = bucket.get_blob(CHROMA_PERSIST)

    # Check if db exists in bucket
    if db_blob:
        db_blob.download_to_filename(CHROMA_PERSIST)

    # Embed files and add vectors to the database
    pages = []
    for fp in filepaths:
        fname = os.path.basename(fp)

        # If a file already exists in the user bucket, skip (no duplicates)
        if fname in blob_names:
            continue

        # Upload the file to Google Cloud
        file_blob = bucket.blob(fname)
        file_blob.upload_from_filename(fp)

        # Document loader (just PDFs for now)
        loader = PyPDFLoader(fp)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=200,
            chunk_overlap=20
        )
        pages.extend(loader.load_and_split(text_splitter))

        # Delete local file
        os.remove(fp)

    if len(pages) > 0:
        # Chroma
        vector_db = Chroma.from_documents(pages, embedding=OpenAIEmbeddings(), persist_directory=CHROMA_PERSIST)
        vector_db.persist()

        # If Chroma DB file available in memory, upload it to cloud
        upload_chroma_db(bucket)


def get_agent_executor_and_respond(query, user_bucket=BUCKET_NAME):
    # If user bucket has a vector db, create a retriever. Otherwise, don't.
    bucket = storage_client.get_bucket(user_bucket)
    blobs = bucket.list_blobs()

    if not os.path.exists(CHROMA_PERSIST):
        os.makedirs(CHROMA_PERSIST)

    for blob in blobs:
        if CHROMA_PERSIST in blob.name:
            if "chroma.sqlite3" not in blob.name:
                chroma_metadir = Path(blob.name).parent.absolute()
                if not os.path.exists(chroma_metadir):
                    os.makedirs(chroma_metadir)
            b = bucket.get_blob(blob.name)
            b.download_to_filename(blob.name)

    if len(os.listdir(CHROMA_PERSIST)) > 0:
        vector_db = Chroma(persist_directory=CHROMA_PERSIST, embedding_function=OpenAIEmbeddings())
        retriever = vector_db.as_retriever(search_kwargs={'k': 3})
    else:
        retriever = None

    # Model
    llm = ChatOpenAI(model="gpt-3.5-turbo-1106", temperature=0.7)

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

    if retriever:
        retriever_tool = create_retriever_tool(retriever, "upload-file-search",
                                               """This tool should be your first resort when searching for information 
                                               to answer a user's query. If no information can be found using this tool,
                                               use Tavily search.""")
        tools = [retriever_tool, search]

    # Upstash Redis chat persistence
    history = UpstashRedisChatMessageHistory(
        url=cfg["UPSTASH_URL"],
        token=cfg["UPSTASH_TOKEN"],
        session_id=user_bucket
    )

    # Memory (include Redis history)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, chat_memory=history)

    # Agent and executor
    agent = create_openai_functions_agent(llm=llm, prompt=prompt, tools=tools)
    agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory)

    response = agent_executor.invoke({"input": query})
    upload_chroma_db(bucket)

    return response["output"]


if __name__ == "__main__":
    pass
