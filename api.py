from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
from main import *
import os

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

TEMP_DIR = "temp_data"


class UserQuery(BaseModel):
    query: str = ""


class UserCredentials(BaseModel):
    email: str
    username: str
    password: str


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
    mysql_register_user(email, username, password)
    return RedirectResponse(url="/chatbot", status_code=302)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request=request, name="home.html", context={}
    )


@app.get("/chatbot")
async def chatbot_page(request: Request):
    upload_user_files_and_db_to_google_cloud([])
    return templates.TemplateResponse(
        request=request, name="chatbot.html", context={}
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
