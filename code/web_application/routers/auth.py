import time
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND


#Get the web_application folder
BASE_DIR = Path(__file__).resolve().parent.parent

#Create the authentication router
router = APIRouter()

#Use the templates folder from any working directory
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

#Demo account for this homework
VALID_USERNAME = "admin"
VALID_PASSWORD = "password"

#Use a short timeout so it is easy to demonstrate
#A production application should use a longer timeout
IDLE_TIMEOUT_SECONDS = 120


def current_user(request: Request):
    """Return the username when the session is active"""

    user = request.session.get("user")

    #The user has not logged in
    if not user:
        return None

    last_seen = request.session.get("last_seen")

    #Clear a missing or expired session
    if last_seen is None or time.time() - last_seen > IDLE_TIMEOUT_SECONDS:
        request.session.clear()
        request.state.session_expired = True
        return None

    #Refresh the sliding idle timeout
    request.session["last_seen"] = time.time()
    return user


@router.get("/")
def home(request: Request):
    """Show the Clinical Trials Portal home page"""

    user = current_user(request)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "user": user,
        },
    )


@router.get("/login")
def login_page(request: Request):
    """Show the login form and an optional error message"""

    user = current_user(request)

    #Send an active user back to the dashboard
    if user:
        return RedirectResponse(
            url="/dashboard",
            status_code=HTTP_302_FOUND,
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "user": None,
            "error": request.query_params.get("error"),
        },
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """Check the account and create a session"""

    if username == VALID_USERNAME and password == VALID_PASSWORD:
        request.session.clear()
        request.session["user"] = username
        request.session["last_seen"] = time.time()

        return RedirectResponse(
            url="/dashboard",
            status_code=HTTP_302_FOUND,
        )

    #Use POST Redirect GET so refreshing does not submit again
    return RedirectResponse(
        url="/login?error=invalid",
        status_code=HTTP_302_FOUND,
    )


@router.get("/dashboard")
def dashboard(request: Request):
    """Only allow an active user to open the dashboard"""

    user = current_user(request)

    if not user:
        expired = getattr(request.state, "session_expired", False)

        if expired:
            login_url = "/login?error=expired"
        else:
            login_url = "/login"

        return RedirectResponse(
            url=login_url,
            status_code=HTTP_302_FOUND,
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "idle_timeout": IDLE_TIMEOUT_SECONDS,
        },
    )


@router.get("/logout")
def logout(request: Request):
    """Clear the session and return to the home page"""

    request.session.clear()

    return RedirectResponse(
        url="/",
        status_code=HTTP_302_FOUND,
    )
