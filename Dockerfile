# 云服务器 / 容器平台部署用（Streamlit Community Cloud 不需要这个文件）
# 构建： docker build -t hiking-map .
# 运行： docker run -d -p 8501:8501 --name hiking-map hiking-map

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

# 时区 + 中文字体（图表里的中文才不会变方块）
RUN apt-get update && apt-get install -y --no-install-recommends \
        tzdata fonts-noto-cjk \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖，利用 Docker 层缓存：改代码不会重装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 非 root 运行，容器被攻破时影响面更小
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health').status==200 else 1)"

CMD ["python", "-m", "streamlit", "run", "Home.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
