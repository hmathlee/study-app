from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
import base64

from main import *
from api_utils import *

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

TEMP_DIR = "temp_data"


class UserQuery(BaseModel):
    query: str = ""


class UserCredentials(BaseModel):
    email: str
    username: str = ""
    password: str = ""


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request=request, name="home.html", context={}
    )


@app.get("/register")
async def register_user(request: Request):
    return templates.TemplateResponse(
        request=request, name="register.html", context={}
    )


@app.post("/register-user")
async def register_user_with_mysql_db(user_creds: UserCredentials):
    email = user_creds.email
    username = user_creds.username
    password = user_creds.password
    return mysql_register_user(email, username, password)


@app.get("/login")
async def login(request: Request):
    return templates.TemplateResponse(
        request=request, name="login.html", context={}
    )


@app.post("/verify-login")
async def user_login(user_creds: UserCredentials):
    email = user_creds.email
    password = user_creds.password
    response = validate_user_login(email, password)
    json_response = JSONResponse(content=response)

    if "username" in response:
        # Generate session ID
        session_id_bytes = os.urandom(16)
        session_id = base64.urlsafe_b64encode(session_id_bytes).decode("utf-8")
        json_response.set_cookie("session_id", session_id, max_age=60)
        insert_session_id(session_id, response["username"])

    return json_response


@app.get("/user/{username}")
async def user_profile(request: Request):
    username = get_username_from_request_cookies(request)
    if username:
        return templates.TemplateResponse(
            request=request, name="profile.html", context={"username": username}
        )
    else:
        return login(request)


@app.get("/logout")
async def logout(request: Request):
    remove_session_id(request)


@app.get("/chatbot")
async def chatbot_page(request: Request):
    upload_user_files_and_db_to_google_cloud([])
    username = get_username_from_request_cookies(request)
    return templates.TemplateResponse(
        request=request, name="chatbot.html", context={"username": username}
    )


@app.post("/chatbot")
async def send_response(user_query: UserQuery):
    query = user_query.query
    if len(query) > 0:
        response = get_agent_executor_and_respond(query)
    else:
        response = "", ""
    return {"result": response}


@app.post("/upload-files")
async def upload_file(payload: UploadFile = File(...)):
    content = await payload.read()
    filename = payload.filename
    fp = os.path.join(TEMP_DIR, filename)

    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    with open(fp, "wb") as f:
        f.write(content)

    return {
        "status": "Uploaded files successfully",
        "filename": filename
    }


@app.post("/upload-to-google-cloud")
async def upload_files_and_db_to_google_cloud():
    fnames = os.listdir(TEMP_DIR)
    fps = [os.path.join(TEMP_DIR, fname) for fname in fnames]
    upload_user_files_and_db_to_google_cloud(fps)

    return {"status": "Uploaded files and DB to Google Cloud successfully"}
