from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from motor.motor_asyncio import AsyncIOMotorClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import json
from typing import List, Dict, Any
import logging
from datetime import datetime, timedelta
import os

from app.models.lovebug_data import LovebugReport, LovebugStats
from app.crawlers.twitter_crawler import TwitterCrawler
from app.api.routes import router
from app.utils.websocket_manager import WebSocketManager

# 로깅 설정
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 전역 변수
mongodb_client = None
database = None
scheduler = None
websocket_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # 시작 시 실행
    global mongodb_client, database, scheduler
    
    # MongoDB 연결
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_client = AsyncIOMotorClient(MONGODB_URL)
    database = mongodb_client.lovebug_map
    
    # 스케줄러 시작
    scheduler = AsyncIOScheduler()
    
    # 10분마다 크롤링 작업 스케줄링
    crawler = TwitterCrawler()
    scheduler.add_job(
        crawl_and_update,
        'interval',
        minutes=10,
        id='lovebug_crawler',
        kwargs={'crawler': crawler}
    )
    
    scheduler.start()
    logger.info("러브버그 맵 백엔드 시작됨")
    
    yield
    
    # 종료 시 실행
    if scheduler:
        scheduler.shutdown()
    if mongodb_client:
        mongodb_client.close()
    logger.info("러브버그 맵 백엔드 종료됨")

# FastAPI 앱 생성
app = FastAPI(
    title="러브버그 맵 API",
    description="SNS 데이터 기반 실시간 러브버그 출몰 지도 서비스",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 제공 (디렉토리가 존재하는 경우에만)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# 라우터 등록
app.include_router(router, prefix="/api/v1")

async def crawl_and_update(crawler: TwitterCrawler):
    """크롤링 작업 수행 및 데이터 업데이트"""
    try:
        logger.info("러브버그 크롤링 시작")
        
        # 트위터 크롤링
        reports = await crawler.crawl_lovebug_tweets()
        
        # 데이터베이스에 저장
        if reports:
            collection = database.lovebug_reports
            for report in reports:
                await collection.update_one(
                    {"tweet_id": report.tweet_id},
                    {"$set": report.dict()},
                    upsert=True
                )
            
            logger.info(f"{len(reports)}개의 러브버그 보고서 업데이트됨")
            
            # 웹소켓을 통해 클라이언트에게 실시간 업데이트 전송
            await websocket_manager.broadcast({
                "type": "lovebug_update",
                "data": [report.dict() for report in reports]
            })
        
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """웹소켓 연결 처리"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 클라이언트로부터 메시지 처리
            await websocket_manager.send_personal_message(
                {"type": "pong", "message": "연결 유지됨"}, 
                websocket
            )
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

@app.get("/")
async def root():
    """헬스체크 엔드포인트"""
    return {
        "message": "러브버그 맵 API가 실행 중입니다",
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "version": "1.0.0",
        "frontend_url": "https://lovebug-map.vercel.app",
        "backend_url": "https://lovebug-map-backend.onrender.com"
    }

@app.get("/health")
async def health_check():
    """상세한 헬스체크"""
    try:
        # MongoDB 연결 확인
        await database.command("ping")
        mongodb_status = "connected"
    except Exception as e:
        mongodb_status = f"error: {str(e)}"
    
    return {
        "api": "running",
        "mongodb": mongodb_status,
        "scheduler": "running" if scheduler and scheduler.running else "stopped",
        "timestamp": datetime.now().isoformat(),
        "cors_origins": os.getenv("ALLOWED_ORIGINS", "*"),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # 프로덕션에서는 reload 비활성화
        log_level="info"
    )