FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 先复制依赖文件，利用缓存
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# 复制当前目录所有代码到容器 /app 下
COPY . .

EXPOSE 8000

# 注意：这里的启动路径变了！
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]