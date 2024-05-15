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

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
import shutil
import random
import string

from api_utils import *

# Config
cfg = yaml.safe_load(open("secrets/secrets.yaml", "r"))

# API keys
os.environ["LANGCHAIN_API_KEY"] = cfg["LANGCHAIN_API_KEY"]
os.environ["OPENAI_API_KEY"] = cfg["OPENAI_API_KEY"]
os.environ["TAVILY_API_KEY"] = cfg["TAVILY_API_KEY"]
os.environ["ALLOW_RESET"] = "True"

# FastAPI
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Paths
TEMP_DIR = "temp_data"


# Pydantic models
class UserQuery(BaseModel):
    query: str = ""


class UserCredentials(BaseModel):
    email: str
    username: str = ""
    password: str = ""


# Define endpoints
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request=request, name="home.html", context={}
    )


@app.get("/register")
async def register(request: Request):
    return templates.TemplateResponse(
        request=request, name="register.html", context={}
    )


@app.post("/register-user")
async def register_user(user_creds: UserCredentials):
    # Collect user credentials
    email = user_creds.email
    username = user_creds.username
    password = user_creds.password

    # Ensure that email is not already in database
    cursor, conn = get_cursor(return_connection=True)
    cursor.execute("SELECT * FROM user_credentials WHERE email=%s", (email,))
    email_exist = cursor.fetchone()
    if email_exist:
        return {"status": "That email is already taken!"}

    # Insert credentials if username and password are present
    if username != "" and password != "":
        cursor.execute("INSERT INTO user_credentials (email, username, password) VALUES (%s, %s, %s)",
                       (email, username, password))

    conn.commit()
    conn.close()
    return {"status": "OK"}


@app.get("/login")
async def login(request: Request):
    return templates.TemplateResponse(
        request=request, name="login.html", context={}
    )


@app.post("/verify-login")
async def user_login(request: Request, user_creds: UserCredentials):
    email = user_creds.email
    password = user_creds.password

    # Validate user login
    cursor = get_cursor()
    cursor.execute("SELECT id FROM user_credentials WHERE email=%s AND password=%s", (email, password))
    user_id = cursor.fetchone()

    # If email and password are correct, query returns a user ID
    if user_id:
        response = {
            "status": "OK",
            "user_id": user_id
        }

    # No user ID is returned for incorrect credentials
    else:
        response = {"status": "Invalid email or password"}

    json_response = JSONResponse(content=response)

    # Once user login is verified, replace temp session ID with actual user ID
    if "user_id" in response:
        remove_session_id(request)
        json_response = set_response_cookie(json_response, response["user_id"])

    return json_response


@app.get("/user/{username}")
async def user_profile(request: Request):
    # Load user info
    context = {}
    for user_detail in ["username", "email", "major", "coins"]:
        context[user_detail] = get_user_credential_from_request_cookies(request, user_detail)

    # If user has an account, username is not None
    if context["username"]:
        return templates.TemplateResponse(
            request=request, name="profile.html", context=context
        )

    # Temp session; prompt user to login in order to access profile
    else:
        return login(request)


@app.post("/user/{username}/update-user")
async def update_user(request: Request, user_creds: UserCredentials):
    # Get the ID of user to update
    user_id = get_user_credential_from_request_cookies(request, "id")

    # Collect credentials
    email = user_creds.email
    username = user_creds.username
    password = user_creds.password

    # Collect current credentials for user in database
    cursor, conn = get_cursor(return_connection=True)
    cursor.execute("SELECT * FROM user_credentials where id=%s", (user_id, ))
    query_result = cursor.fetchone()
    curr_creds = dict([(desc[0], q) for desc, q in zip(cursor.description, query_result)])

    # Update user row
    cursor, conn = get_cursor(return_connection=True)
    cursor.execute("UPDATE user_credentials SET email=%s, username=%s, password=%s where id=%s",
                   (email if email != "" else curr_creds["email"],
                    username if username != "" else curr_creds["username"],
                    password if password != "" else curr_creds["password"],
                    user_id))
    conn.commit()
    conn.close()


@app.get("/logout")
async def logout(request: Request):
    user_id = get_user_credential_from_request_cookies(request, "id")
    if "temp" in user_id:
        remove_temp_bucket("study-app-user-" + user_id)
    remove_session_id(request)
    return chatbot_page(request)


@app.get("/chatbot")
async def chatbot_page(request: Request):
    user_id = get_user_credential_from_request_cookies(request, "id")

    # Initial chatbot page load
    if user_id is None:
        username = None

    # Handles chatbot page reload when user is not logged in
    elif "temp" in user_id:
        remove_temp_bucket("study-app-user-" + user_id)
        remove_session_id(request)
        username = None

    # Reload when user is logged in
    else:
        username = get_user_credential_from_request_cookies(request, "username")

    # Preserve current state if user is logged in
    if username:
        response = templates.TemplateResponse(
            request=request, name="chatbot.html", context={"username": username}
        )

    # If not logged in, fresh start
    else:
        response = templates.TemplateResponse(
            request=request, name="chatbot.html", context={}
        )
        temp_id = "temp-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        response = set_response_cookie(response, temp_id)

    return response


@app.post("/chatbot")
async def send_response(request: Request, user_query: UserQuery):
    query = user_query.query
    user_id = get_user_credential_from_request_cookies(request, "id")
    user_id = "study-app-user-" + user_id

    # If user has a vector db in GCS, create a retriever. Otherwise, don't.
    buckets = storage_client.list_buckets()
    buckets = [bucket.name for bucket in buckets]
    pages = []

    # If user bucket not in cloud storage, create the bucket
    if user_id not in buckets:
        storage_client.create_bucket(user_id)
    else:
        bucket = storage_client.get_bucket(user_id)
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
    ttl = 60 if "temp" in user_id else -1
    history = UpstashRedisChatMessageHistory(
        url=cfg["UPSTASH_URL"],
        token=cfg["UPSTASH_TOKEN"],
        session_id=user_id,
        ttl=ttl
    )

    # Memory (include Redis history)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, chat_memory=history)

    # Agent and executor
    agent = create_openai_functions_agent(llm=llm, prompt=prompt, tools=tools)
    agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory)

    # Invoke to get response
    response = await agent_executor.ainvoke({"input": query})

    return {"result": response["output"]}


@app.post("/upload-files")
async def upload_file(request: Request, payload: UploadFile = File(...)):
    # Read in the file
    content = await payload.read()
    filename = payload.filename

    # Set up a temporary directory for user (temp if not logged in)
    user_id = get_user_credential_from_request_cookies(request, "id")
    user_id = "study-app-user-" + user_id
    temp_data_dir = TEMP_DIR + "_" + user_id
    fp = os.path.join(temp_data_dir, filename)
    if not os.path.exists(temp_data_dir):
        os.makedirs(temp_data_dir)

    # Local file upload
    with open(fp, "wb") as f:
        f.write(content)

    return {
        "status": "Uploaded files successfully",
        "filename": filename
    }


@app.post("/upload-to-google-cloud")
async def upload_to_google_cloud(request: Request):
    # Get user whose files need to be uploaded
    user_id = get_user_credential_from_request_cookies(request, "id")
    user_id = "study-app-user-" + user_id

    # Get blobs from user GCS bucket; create if it doesn't exist
    buckets = storage_client.list_buckets()
    buckets = [bucket.name for bucket in buckets]
    if user_id not in buckets:
        bucket = storage_client.create_bucket(user_id)
    else:
        bucket = storage_client.get_bucket(user_id)

    blobs = bucket.list_blobs()
    blob_names = [blob.name for blob in blobs]

    # Retrieve user files
    temp_data_dir = TEMP_DIR + "_" + user_id
    fnames = os.listdir(temp_data_dir)
    fps = [os.path.join(temp_data_dir, fname) for fname in fnames]

    # Upload files to Google Cloud
    for fp in fps:
        fname = os.path.basename(fp)

        # If a file already exists in the user bucket, skip (no duplicates)
        if fname in blob_names:
            continue

        # Upload the file to Google Cloud
        file_blob = bucket.blob(fname)
        file_blob.upload_from_filename(fp)

    # Remove the temp dir when done
    shutil.rmtree(temp_data_dir)

    return {"status": "Uploaded files and DB to Google Cloud successfully"}
