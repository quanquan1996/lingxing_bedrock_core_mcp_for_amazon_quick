"""Test invoking the deployed MCP server via AgentCore endpoint"""
import asyncio
import boto3
import base64
import requests

# ============================================================
# Fill in your own values below
# ============================================================
REGION = "<REGION>"                    # e.g. "us-west-2"
USER_POOL_ID = "<USER_POOL_ID>"        # e.g. "us-west-2_AbCdEfGhI"
CLIENT_ID = "<COGNITO_CLIENT_ID>"      # e.g. "1abc2def3ghi4jkl5mno"
AGENT_ARN = "arn:aws:bedrock-agentcore:<REGION>:<ACCOUNT_ID>:runtime/<AGENT_ID>"
COGNITO_DOMAIN = "<COGNITO_DOMAIN>"    # e.g. "us-west-2abcdefghi"

# 1. Get Cognito token
idp = boto3.client("cognito-idp", region_name=REGION)
client_info = idp.describe_user_pool_client(
    UserPoolId=USER_POOL_ID, ClientId=CLIENT_ID
)
client_secret = client_info["UserPoolClient"]["ClientSecret"]

token_url = f"https://{COGNITO_DOMAIN}.auth.{REGION}.amazoncognito.com/oauth2/token"

auth_b64 = base64.b64encode(f"{CLIENT_ID}:{client_secret}".encode()).decode()
resp = requests.post(
    token_url,
    headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_b64}",
    },
    data={"grant_type": "client_credentials", "scope": "lingxing-mcp/invoke"},
)
token_data = resp.json()
if "access_token" not in token_data:
    print(f"Token error: {token_data}")
    exit(1)
access_token = token_data["access_token"]
print(f"Got access token: {access_token[:30]}...")

# 2. Build MCP URL (per AWS docs)
encoded_arn = AGENT_ARN.replace(":", "%3A").replace("/", "%2F")
mcp_url = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
print(f"MCP URL: {mcp_url}")

# 3. Use MCP client
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    headers = {
        "authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    print(f"\nConnecting to MCP server...")
    async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
        read_stream, write_stream, _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Initialized!")

            # List tools
            tools = await session.list_tools()
            print(f"\nAvailable tools ({len(tools.tools)}):")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description[:60] if t.description else ''}")

asyncio.run(main())
