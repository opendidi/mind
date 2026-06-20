# ==========================================================================
# mind — 图形可视化编辑器 Docker 镜像
# 基于 Python 3.12，Flask + Agent 系统
# 已配置国内镜像源（清华源），解决 pip/apt 下载超时问题
# ==========================================================================

FROM python:3.12-slim

# ── 系统依赖（apt 阿里云镜像源） ────────────────────────────────────────────
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && echo "deb http://mirrors.aliyun.com/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list \
    && echo "deb http://mirrors.aliyun.com/debian bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    && echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    curl \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# ── 工作目录 ───────────────────────────────────────────────────────────────
WORKDIR /app

# ── pip 阿里云镜像源 ────────────────────────────────────────────────────────
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# ── Python 依赖（利用 Docker 层缓存） ───────────────────────────────────────
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch==2.5.1 \
    && pip install --no-cache-dir -r requirements.txt

# ── 应用代码 ───────────────────────────────────────────────────────────────
COPY . .

# ── 前端静态资源（如果 web/dist 存在则复制） ───────────────────────────────
# 构建前端后取消下面注释：
# COPY web/dist /app/app/static

# ── 运行时配置 ─────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=starter.py

EXPOSE 5001

# ── 启动 ───────────────────────────────────────────────────────────────────
CMD ["python", "starter.py"]
