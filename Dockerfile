FROM python:3.12-slim

WORKDIR /app

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Aerich 迁移配置
COPY aerich.ini ./ 
COPY migrations/ ./migrations/
COPY scripts/deploy.sh ./scripts/

EXPOSE 8000

CMD sh -c "aerich upgrade && uvicorn src.main:app --host 0.0.0.0 --port 8000"
