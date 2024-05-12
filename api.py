import string

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel

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


class UserUpdate(BaseModel):
    detail: str


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

    if "user_id" in response:
        json_response = set_response_cookie(json_response, response["user_id"])

    return json_response


@app.get("/user/{username}")
async def user_profile(request: Request):
    context = {}
    for user_detail in ["username", "email", "major", "coins"]:
        context[user_detail] = get_user_credential_from_request_cookies(request, user_detail)
    if context["username"]:
        return templates.TemplateResponse(
            request=request, name="profile.html", context=context
        )
    else:
        return login(request)


@app.get("/update-user/{username}/{detail}")
async def update_user(request: Request, user_update: UserUpdate):
    context = {}
    for user_detail in ["username", "email", "major", "coins"]:
        context[user_detail] = get_user_credential_from_request_cookies(request, user_detail)
    context["detail"] = user_update.detail
    if context["username"]:
        return templates.TemplateResponse(
            request=request, name="profile.html", context=context
        )
    else:
        return login(request)


@app.get("/logout")
async def logout(request: Request):
    user_id = get_user_id_from_request_cookies(request)
    user_id = get_gcs_user_id(user_id)
    if "temp" in user_id:
        remove_temp_bucket(user_id)
    remove_session_id(request)
    return templates.TemplateResponse(
        request=request, name="chatbot.html", context={}
    )


@app.get("/chatbot")
async def chatbot_page(request: Request):
    username = get_user_credential_from_request_cookies(request, "username")
    if username:
        response = templates.TemplateResponse(
            request=request, name="chatbot.html", context={"username": username}
        )
    else:
        temp_id = "temp-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        response = templates.TemplateResponse(
            request=request, name="chatbot.html", context={}
        )
        response = set_response_cookie(response, temp_id)

    return response


@app.post("/chatbot")
async def send_response(request: Request, user_query: UserQuery):
    user_id = get_user_id_from_request_cookies(request)
    user_id = get_gcs_user_id(user_id)

    query = user_query.query
    if len(query) > 0:
        response = await get_agent_executor_and_respond(query, user_id)
    else:
        response = "", ""
    return {"result": response}
    # return {"result": "Response goes here"}


@app.post("/upload-files")
async def upload_file(request: Request, payload: UploadFile = File(...)):
    content = await payload.read()
    filename = payload.filename

    # Set up a temporary directory for user (temp if not logged in)
    user_id = get_user_id_from_request_cookies(request)
    user_id = get_gcs_user_id(user_id)
    temp_data_dir = TEMP_DIR + "_" + user_id

    fp = os.path.join(temp_data_dir, filename)
    if not os.path.exists(temp_data_dir):
        os.makedirs(temp_data_dir)

    with open(fp, "wb") as f:
        f.write(content)

    return {
        "status": "Uploaded files successfully",
        "filename": filename
    }


@app.post("/upload-to-google-cloud")
async def upload_files_and_db_to_google_cloud(request: Request):
    user_id = get_user_id_from_request_cookies(request)
    user_id = get_gcs_user_id(user_id)

    temp_data_dir = TEMP_DIR + "_" + user_id
    fnames = os.listdir(temp_data_dir)
    fps = [os.path.join(temp_data_dir, fname) for fname in fnames]
    upload_user_files_and_db_to_google_cloud(fps, user_id)

    return {"status": "Uploaded files and DB to Google Cloud successfully"}
