FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pycryptodome

# 复制代码
COPY lingxing_client.py .
COPY mcp_server.py .

# AgentCore 要求: 0.0.0.0:8000
EXPOSE 8000

CMD ["python", "mcp_server.py"]
