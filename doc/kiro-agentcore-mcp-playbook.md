# Kiro + AgentCore MCP 部署手册

> 基于领星 ERP 经营数据 MCP 项目的实战经验整理
> 适用于在新 AWS 账号上用 Kiro 快速复制部署

---

## 一、整体架构

```
用户 → Quick Suite (Chat/Flows)
        ↓ OAuth Token
   Cognito (Client Credentials Grant)
        ↓ Bearer Token
   AgentCore Runtime (MCP Server)
        ↓ API 调用
   业务 API (领星 ERP OpenAPI)
        ↓ Excel 报告
   S3 (预签名 URL 下载)
```

## 二、前置条件

- AWS 账号，有 IAM 管理权限
- Windows 环境需要：Python 3.10+、chocolatey（装 zip）
- 业务 API 的凭证（本例为领星 AppId/AppSecret）

## 三、Kiro 交互流程

### 第 1 步：让 Kiro 生成 MCP Server 代码

给 Kiro 的 prompt 示例：

```
我有一份业务 API 文档（附上 doc/xxx-api-guide.md），
需要把这些 API 封装成 MCP Server，部署到 AWS AgentCore，
在 Quick Suite 里使用。参考这篇博客的架构：
https://aws.amazon.com/cn/blogs/china/quick-suite-agent-core-kiro-logistics-quote-assistant/
```

Kiro 会生成：
- `mcp-server/mcp_server.py` — MCP Server 主入口
- `mcp-server/xxx_client.py` — 业务 API 客户端
- `mcp-server/requirements.txt` — Python 依赖
- `mcp-server/Dockerfile` — 容器镜像（备用）
- `mcp-server/.bedrock_agentcore.yaml` — AgentCore 部署配置

### 第 2 步：让 Kiro 配置 AWS 资源

prompt：

```
我当前环境已经有权限的 IAM，帮我完成 .bedrock_agentcore.yaml 的配置
```

Kiro 会自动执行以下操作：

#### 2.1 获取账号信息
```bash
aws sts get-caller-identity
aws configure get region
```

#### 2.2 查找现有 AgentCore Runtime Role
```bash
aws iam list-roles --query "Roles[?contains(RoleName, 'AgentCore')].{Name:RoleName,Arn:Arn}"
```
> 如果没有，需要先在 AgentCore 控制台创建一个 Agent 让它自动生成 Role

#### 2.3 创建 Cognito 资源

创建 Resource Server（Client Credentials Grant 必需）：
```bash
aws cognito-idp create-resource-server \
  --user-pool-id <POOL_ID> \
  --identifier "your-mcp" \
  --name "Your MCP Server" \
  --scopes "ScopeName=invoke,ScopeDescription=Invoke MCP tools" \
  --region <REGION>
```

创建 App Client：
```bash
aws cognito-idp create-user-pool-client \
  --user-pool-id <POOL_ID> \
  --client-name "your-mcp-agentcore" \
  --generate-secret \
  --allowed-o-auth-flows "client_credentials" \
  --allowed-o-auth-scopes "your-mcp/invoke" \
  --allowed-o-auth-flows-user-pool-client \
  --region <REGION>
```
> 记录返回的 ClientId 和 ClientSecret，Quick Suite 配置时需要用到

查看已创建的 Client Secret（如果忘记了）：
```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id <POOL_ID> \
  --client-id <CLIENT_ID> \
  --query "UserPoolClient.ClientSecret" \
  --output text \
  --region <REGION>
```

#### 2.4 创建 S3 桶
```bash
aws s3 mb s3://your-reports-<ACCOUNT_ID> --region <REGION>
```

#### 2.5 给 AgentCore Role 添加 S3 权限

创建 policy json 文件（避免 PowerShell 转义问题）：
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::your-reports-bucket",
      "arn:aws:s3:::your-reports-bucket/*"
    ]
  }]
}
```
```bash
aws iam put-role-policy \
  --role-name <AGENTCORE_ROLE_NAME> \
  --policy-name "S3ReportAccess" \
  --policy-document file://s3-policy.json
```

#### 2.6 创建 CodeBuild 用的 S3 桶
```bash
aws s3 mb s3://bedrock-agentcore-codebuild-<ACCOUNT_ID> --region <REGION>
```

### 第 3 步：让 Kiro 部署

prompt：

```
AppId 是 xxx，AppSecret 是 yyy，帮我完成所有部署工作
```

Kiro 会执行以下操作：

#### 3.1 安装依赖（首次）
```bash
py -3 -m pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit
choco install zip -y   # Windows 必需，agentcore deploy 依赖 zip 命令
```

#### 3.2 部署
```bash
agentcore deploy -a <AGENT_NAME> \
  --auto-update-on-conflict \
  --env "YOUR_APP_ID=xxx" \
  --env "YOUR_APP_SECRET=yyy" \
  --env "YOUR_S3_BUCKET=bucket-name" \
  --env "YOUR_S3_PREFIX=prefix/"
```

> 必须在 mcp-server/ 目录下执行（.bedrock_agentcore.yaml 所在目录）

#### 3.3 验证
```bash
agentcore status
```

### 第 4 步：测试 MCP 端点

MCP 端点 URL 格式：
```
https://bedrock-agentcore.<REGION>.amazonaws.com/runtimes/<ENCODED_AGENT_ARN>/invocations?qualifier=DEFAULT
```

其中 ENCODED_AGENT_ARN 是把 `:` 替换为 `%3A`，`/` 替换为 `%2F`。

测试脚本核心逻辑：
```python
# 1. 获取 Cognito Token
token_url = f"https://<DOMAIN>.auth.<REGION>.amazoncognito.com/oauth2/token"
# POST grant_type=client_credentials, scope=your-mcp/invoke
# Authorization: Basic base64(client_id:client_secret)

# 2. 用 MCP 客户端连接
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

headers = {"authorization": f"Bearer {token}", "Content-Type": "application/json"}
async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (r, w, _):
    async with ClientSession(r, w) as session:
        await session.initialize()
        tools = await session.list_tools()
```

### 第 5 步：Quick Suite 配置

1. Quick Suite → Integrations → Actions → 添加 MCP Server
2. 填入 MCP 端点 URL
3. 认证方式选择「服务身份验证」（不是用户身份验证）
4. 身份验证类型：基于用户的自定义 OAuth
5. 填写以下信息：
   - 客户端 ID：Cognito App Client ID
   - 客户端密钥：Cognito App Client Secret（创建时返回，或用 describe-user-pool-client 查询）
   - Token URL：`https://<COGNITO_DOMAIN>.auth.<REGION>.amazoncognito.com/oauth2/token`
   - Scope：`<RESOURCE_SERVER_ID>/invoke`（如 `lingxing-mcp/invoke`）
6. 创建 Flows 编排业务流程

> Cognito Domain 查询：`aws cognito-idp describe-user-pool --user-pool-id <POOL_ID> --query "UserPool.Domain" --output text`
> Token URL 中的 domain 就是这个值

---

## 四、踩坑记录

### 4.1 YAML 编码问题（Windows）
**现象**：agentcore deploy 报 `UnicodeDecodeError: 'charmap' codec can't decode byte`
**原因**：Windows 默认 cp1252 编码无法处理 YAML 中的中文注释
**解决**：`.bedrock_agentcore.yaml` 中不要写中文，全部用英文或纯 ASCII

### 4.2 缺少 zip 命令（Windows）
**现象**：`zip utility is required for direct_code_deploy deployment but was not found`
**解决**：`choco install zip -y`

### 4.3 AgentCore 运行时 /var/ 只读
**现象**：第三方库写日志到 /var/ 导致启动失败
**解决**：在 import 第三方库之前 patch logging.FileHandler，重定向到 /tmp/
```python
import logging
_orig = logging.FileHandler.__init__
def _patched(self, filename, mode="a", encoding=None, delay=False, errors=None):
    if filename.startswith("/var/"):
        filename = "/tmp/" + os.path.basename(filename)
    _orig(self, filename, mode, encoding, delay, errors)
logging.FileHandler.__init__ = _patched
```

### 4.4 AgentCore 无状态运行时
**现象**：生成的文件在后续请求中找不到
**解决**：文件生成和 S3 上传必须在同一个 tool 调用中原子完成

### 4.5 Cognito Client Credentials 没有 aud claim
**现象**：AgentCore JWT 验证 allowedAudience 失败
**解决**：在 .bedrock_agentcore.yaml 中用 `allowedClients` 而不是 `allowedAudience`

### 4.6 PowerShell 中 JSON 转义问题
**现象**：`aws iam put-role-policy --policy-document '{...}'` 报错
**解决**：把 JSON 写到文件里，用 `file://xxx.json` 引用

### 4.7 MCP Server 必须配置
**要求**：`host="0.0.0.0"`, `port=8000`, `stateless_http=True`
```python
mcp = FastMCP(name="xxx", host="0.0.0.0", port=8000, stateless_http=True)
```

### 4.8 agentcore CLI 不在 PATH
**现象**：安装后找不到 agentcore 命令
**解决**：手动加 PATH
```powershell
$env:PATH = "C:\Users\<USER>\AppData\Local\Programs\Python\Python312\Scripts;" + $env:PATH
```

---

## 五、.bedrock_agentcore.yaml 模板

```yaml
default_agent: your_mcp_agent

agents:
  your_mcp_agent:
    name: your_mcp_agent
    entrypoint: mcp_server.py
    deployment_type: direct_code_deploy
    runtime_type: PYTHON_3_11
    platform: linux/arm64
    source_path: .
    aws:
      execution_role: arn:aws:iam::<ACCOUNT>:role/service-role/<AGENTCORE_ROLE>
      execution_role_auto_create: false
      account: "<ACCOUNT_ID>"
      region: <REGION>
      s3_path: s3://bedrock-agentcore-codebuild-<ACCOUNT_ID>
      s3_auto_create: false
      network_configuration:
        network_mode: PUBLIC
      protocol_configuration:
        server_protocol: MCP
      observability:
        enabled: true
    memory:
      mode: NO_MEMORY
    authorizer_configuration:
      customJWTAuthorizer:
        discoveryUrl: https://cognito-idp.<REGION>.amazonaws.com/<POOL_ID>/.well-known/openid-configuration
        allowedClients:
          - <COGNITO_CLIENT_ID>
```

---

## 六、快速复制到新账号的 Checklist

- [ ] 确认新账号有 AgentCore Runtime Role（或先在控制台创建一个 Agent）
- [ ] 确认有 Cognito User Pool（或新建一个）+ Domain 已配置
- [ ] 创建 Resource Server + Client Credentials App Client
- [ ] 创建 S3 报告桶 + CodeBuild 桶
- [ ] 给 AgentCore Role 加 S3 权限
- [ ] 修改 .bedrock_agentcore.yaml 中的账号/Region/Role/Cognito/S3 信息
- [ ] 安装 agentcore CLI + zip（Windows）
- [ ] 在 mcp-server/ 目录执行 `agentcore deploy` 并传入环境变量
- [ ] 用测试脚本验证 MCP 端点
- [ ] 在 Quick Suite 配置 MCP Action 和 Flows
