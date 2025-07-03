#!/bin/bash

# Render 배포용 시작 스크립트
echo "Starting Lovebug Map Backend..."

# 환경 변수 확인
echo "PORT: $PORT"
echo "MONGODB_URL: $MONGODB_URL"

# 애플리케이션 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT 