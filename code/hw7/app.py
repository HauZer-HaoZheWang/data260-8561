"""Minimal upload-and-run UI for the bike-share MRKL exercise."""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from bike_agent import csv_sql, policy_retriever

app = FastAPI(title="HW7 Bike Membership Agent")


@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><html><body><h1>Bike Membership Agent</h1>
    <form action='/run' method='post' enctype='multipart/form-data'>
    <label>Trip CSV <input type='file' name='csv_file' required></label><br>
    <label>Pricing URL <input name='pricing_url' value='https://example.local/pricing' required></label><br>
    <button>Run</button></form><div id='timeline'></div><div id='result'></div></body></html>"""


@app.post("/run")
async def run(csv_file: UploadFile = File(...), pricing_url: str = Form(...)):
    with tempfile.TemporaryDirectory(prefix="hw7-bike-") as temp:
        path = Path(temp) / (csv_file.filename or "trips.csv")
        path.write_bytes(await csv_file.read())
        query = csv_sql(path, "SELECT COUNT(*) AS rides, AVG(duration_min) AS avg_duration FROM trips")
        policy = policy_retriever(pricing_url, "monthly membership included minutes unlock fee")
    return JSONResponse({"timeline": [{"tool": "csv_sql", "observation": query}, {"tool": "policy_retriever", "observation": policy}], "result": {"stop_reason": "success", "steps": 2}})
