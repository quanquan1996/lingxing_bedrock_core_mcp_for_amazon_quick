# Deployment Info

## AgentCore MCP Server

- Agent Name: lingxing_erp_mcp
- Agent ARN: arn:aws:bedrock-agentcore:<REGION>:<ACCOUNT_ID>:runtime/<AGENT_ID>
- Endpoint: DEFAULT (READY)
- Region: <REGION>
- Protocol: MCP (Streamable HTTP)

## MCP Endpoint URL

```
https://bedrock-agentcore.<REGION>.amazonaws.com/runtimes/<ENCODED_AGENT_ARN>/invocations?qualifier=DEFAULT
```

## Cognito OAuth

- User Pool ID: <REGION>_<POOL_ID>
- Client ID: <COGNITO_CLIENT_ID>
- Client Secret: <COGNITO_CLIENT_SECRET>
- Token URL: https://<COGNITO_DOMAIN>.auth.<REGION>.amazoncognito.com/oauth2/token
- Scope: lingxing-mcp/invoke
- Grant Type: client_credentials

## S3

- Bucket: lingxing-reports-<ACCOUNT_ID>
- Prefix: lingxing-reports/

## Available MCP Tools (9)

1. get_seller_list
2. get_daily_profit
3. get_weekly_profit_summary
4. get_monthly_profit_summary
5. get_profit_by_msku
6. get_negative_reviews
7. get_today_negative_reviews
8. generate_profit_report_excel
9. generate_negative_review_report_excel

## Quick Suite Configuration

In Quick Suite > Integrations > Actions:
1. Add MCP Server action
2. Use the MCP Endpoint URL above
3. Configure OAuth with Cognito Client ID and Secret
4. Create Flows for daily profit analysis and negative review monitoring
