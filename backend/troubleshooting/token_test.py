"""
Simple token test for Azure AD using client credentials.

Usage:
  # from PowerShell (activate your venv if needed)
  python .\backend\troubleshooting\token_test.py

The script reads SLA_BOT_APP_ID and SLA_BOT_APP_PASSWORD from backend/.env
and attempts to get a token for the Bot Framework scope.
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

HERE = os.path.dirname(__file__)
ENV_PATH = os.path.join(HERE, '.env')
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

tenant = os.getenv('AZURE_TENANT_ID') or os.getenv('TENANT_ID') or os.getenv('BOT_TENANT_ID')
client_id = os.getenv('SLA_BOT_APP_ID')
client_secret = os.getenv('SLA_BOT_APP_PASSWORD')
scope = os.getenv('BOT_OAUTH_SCOPE') or 'https://api.botframework.com/.default'

if not tenant:
    print('ERROR: Tenant ID not found in .env (AZURE_TENANT_ID / TENANT_ID).')
    print('Please add your tenant id to backend/.env as AZURE_TENANT_ID and re-run.')
    sys.exit(2)

if not client_id or not client_secret:
    print('ERROR: SLA_BOT_APP_ID or SLA_BOT_APP_PASSWORD not found in backend/.env')
    sys.exit(2)

token_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'

data = {
    'client_id': client_id,
    'scope': scope,
    'client_secret': client_secret,
    'grant_type': 'client_credentials',
}

print('Requesting token from:', token_url)
print('Using client_id:', client_id)
print('Using scope:', scope)

resp = requests.post(token_url, data=data)

print('\nHTTP status:', resp.status_code)
try:
    js = resp.json()
    print(json.dumps(js, indent=2))
except Exception:
    print('Response content:\n', resp.text)

if resp.status_code != 200:
    print('\nToken request failed. If this works locally but the bot still fails,')
    print('the issue is likely in the bot code (token parsing) or network egress from')
    print('the Flask process. Share the JSON above (redact secrets) and I will advise next.')
else:
    print('\nToken fetch succeeded. That indicates your App ID and secret are valid and Azure AD is returning a token.')
