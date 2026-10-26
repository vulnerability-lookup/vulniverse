from flask import request
from . import api_bp


@api_bp.post("/patch2vuln/jobs")
def submit_jobs():
    payload = request.get_json() 
