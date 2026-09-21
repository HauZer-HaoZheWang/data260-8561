import os
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from routers.auth import router as auth_router


#Get the web_application folder
BASE_DIR = Path(__file__).resolve().parent

#This is the assigned port for SID4 8561
PORT_BASE = 8461

#Create the FastAPI application
app = FastAPI(
    title="Clinical Trial API",
    version="1.0.0"
)

#Read session settings from environment variables
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-only-secret-key"
)

#Use false for local HTTP and true for the HTTPS test
COOKIE_SECURE = os.getenv(
    "COOKIE_SECURE",
    "0"
) == "1"

#Add signed cookie session support
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    https_only=COOKIE_SECURE,
    same_site="lax",
    max_age=3600
)

#Add Homework 3 authentication routes
app.include_router(auth_router)

#Make files inside static available through /static
app.mount(
    "/static",
    StaticFiles(
        directory=str(BASE_DIR / "static")
    ),
    name="static"
)


#Trial is the complete data returned by server.
class Trial(BaseModel):
    id: int
    brief_title: str
    sponsor: str


#TrialCreate is the data client sends when creating a trial
#Client does not provide id because server creates it.
class TrialCreate(BaseModel):
    brief_title: str
    sponsor: str


#TrialUpdate is the data client sends when updating a trial.
class TrialUpdate(BaseModel):
    brief_title: str
    sponsor: str


#Use a list as temporary memory storage
#All data will reset after server restarts.
trials: List[Trial] = [
    Trial(
        id=1,
        brief_title="Diabetes Prevention Study",
        sponsor="Stanford University"
    ),
    Trial(
        id=2,
        brief_title="New Treatment for Lung Cancer",
        sponsor="National Cancer Institute"
    ),
    Trial(
        id=3,
        brief_title="Sleep and Memory Research",
        sponsor="University of California"
    ),
]


#Return the Homework 2 CRUD frontend page.
@app.get("/trials")
def trials_ui():
    return FileResponse(
        BASE_DIR / "static" / "index.html"
    )


#Return all trials or search by title and sponsor
@app.get(
    "/api/trials",
    response_model=List[Trial]
)
def get_trials(
    q: Optional[str] = Query(default=None)
):
    #If q is missing or empty, return all trials.
    if q is None or not q.strip():
        return trials

    #Remove spaces and change search text to lowercase
    search_text = q.strip().lower()

    #Return trials whose title or sponsor contains the search text.
    return [
        trial
        for trial in trials
        if (
            search_text in trial.brief_title.lower()
            or search_text in trial.sponsor.lower()
        )
    ]


#Return one trial by its id.
@app.get(
    "/api/trials/{trial_id}",
    response_model=Trial
)
def get_trial(trial_id: int):
    #Go through every trial and find the same id
    for trial in trials:
        if trial.id == trial_id:
            return trial

    #Return 404 if the trial does not exist.
    raise HTTPException(
        status_code=404,
        detail="Trial not found"
    )


#Create a new trial
@app.post(
    "/api/trials",
    response_model=Trial,
    status_code=201
)
def create_trial(
    trial_data: TrialCreate
):
    #Find the largest current id and add one.
    new_id = max(
        [trial.id for trial in trials],
        default=0
    ) + 1

    #Create a complete Trial object with server generated id
    new_trial = Trial(
        id=new_id,
        brief_title=trial_data.brief_title,
        sponsor=trial_data.sponsor
    )

    #Save the new trial into memory.
    trials.append(new_trial)

    return new_trial


#Update an existing trial by its id.
@app.put(
    "/api/trials/{trial_id}",
    response_model=Trial
)
def update_trial(
    trial_id: int,
    trial_data: TrialUpdate
):
    #Use enumerate to get both index and trial
    for index, trial in enumerate(trials):
        if trial.id == trial_id:
            updated_trial = Trial(
                id=trial_id,
                brief_title=trial_data.brief_title,
                sponsor=trial_data.sponsor
            )

            #Replace the old trial with updated trial.
            trials[index] = updated_trial

            return updated_trial

    #Return 404 if the trial does not exist
    raise HTTPException(
        status_code=404,
        detail="Trial not found"
    )


#Delete a trial by its id
@app.delete("/api/trials/{trial_id}")
def delete_trial(
    trial_id: int
):
    #Use enumerate to find its position in the list.
    for index, trial in enumerate(trials):
        if trial.id == trial_id:
            deleted_trial = trials.pop(index)

            return {
                "message": "Trial deleted successfully",
                "trial": deleted_trial
            }

    #Return 404 if the trial does not exist.
    raise HTTPException(
        status_code=404,
        detail="Trial not found"
    )


#Run the application in HTTP or HTTPS mode.
if __name__ == "__main__":
    ssl_dir = BASE_DIR / "certs"
    use_https = (ssl_dir / "cert.pem").exists() and COOKIE_SECURE

    if use_https:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=PORT_BASE,
            ssl_keyfile=str(ssl_dir / "key.pem"),
            ssl_certfile=str(ssl_dir / "cert.pem"),
        )
    else:
        uvicorn.run(app, host="127.0.0.1", port=PORT_BASE)