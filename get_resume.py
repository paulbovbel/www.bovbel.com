#!/usr/bin/env python
import argparse
import json
import pathlib
import sys

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

scopes = ['https://www.googleapis.com/auth/drive.readonly']
document_id = '1sXhQBVv2Xy5NoTsg4JvHLNmKrbC5PgRNghsUXqPWh0A'
creds_file = pathlib.Path('secret/token.json')
resume_file = pathlib.Path('static/resume.pdf')

def main(secrets_file=None):
    if secrets_file:
        if not sys.__stdin__.isatty():
            raise RuntimeError("Token creation must be run from an interactive shell")

        flow = InstalledAppFlow.from_client_secrets_file(secrets_file, scopes)
        creds = flow.run_local_server(port=0)
        creds_file.write_text(creds.to_json())
        print(f"Please add {creds_file} to GitHub repo secrets.")

    else:
        creds = Credentials(**json.loads(creds_file.read_bytes()))

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError("Invalid credentials, unable to refresh")

    service = build('drive', 'v3', credentials=creds)

    resume_data = service.files().export(fileId=document_id, mimeType='application/pdf').execute()
    resume_file.write_bytes(resume_data)


if __name__== "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--secrets-file", type=pathlib.Path, required=False)
    args = parser.parse_args()
    main(**vars(args))
