FROM python:3.12-slim

WORKDIR /app

# 安装依赖（requirements.txt 不含 openai，因国内镜像可能缺失）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir openai>=1.0.0 -i https://pypi.org/simple
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY app/ ./app/

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
