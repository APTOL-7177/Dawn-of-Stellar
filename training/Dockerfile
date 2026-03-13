FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# requirements 먼저 복사 (캐시 레이어 활용)
COPY training/requirements_training.txt /app/requirements_training.txt
RUN pip install --no-cache-dir -r requirements_training.txt

# 게임 소스 복사
COPY src/ /app/src/
COPY config.yaml /app/config.yaml
COPY data/ /app/data/
COPY training/ /app/training/

ENV PYTHONPATH=/app

ENTRYPOINT ["python", "training/train.py"]
