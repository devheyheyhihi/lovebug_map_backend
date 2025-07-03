from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import DESCENDING

from app.models.lovebug_data import (
    LovebugReport, LovebugStats, HotSpot, SearchFilter, 
    SeverityLevel, Platform, Location
)

logger = logging.getLogger(__name__)
router = APIRouter()

# 데이터베이스 의존성 주입
async def get_database() -> AsyncIOMotorDatabase:
    """데이터베이스 연결 반환"""
    # 실제 구현에서는 main.py에서 설정된 database 인스턴스 사용
    from app.main import database
    return database

@router.get("/reports", response_model=List[LovebugReport])
async def get_reports(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    severity: Optional[SeverityLevel] = None,
    platform: Optional[Platform] = None,
    hours: Optional[int] = Query(None, ge=1, le=168, description="최근 N시간 내 데이터"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """러브버그 보고서 목록 조회"""
    try:
        query = {}
        
        # 심각도 필터
        if severity:
            query["severity"] = severity.value
        
        # 플랫폼 필터
        if platform:
            query["platform"] = platform.value
        
        # 시간 필터
        if hours:
            since = datetime.now() - timedelta(hours=hours)
            query["created_at"] = {"$gte": since}
        
        # 데이터 조회
        collection = db.lovebug_reports
        cursor = collection.find(query).sort("created_at", DESCENDING).skip(offset).limit(limit)
        
        reports = []
        async for doc in cursor:
            # MongoDB ObjectId를 문자열로 변환
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            reports.append(LovebugReport(**doc))
        
        return reports
        
    except Exception as e:
        logger.error(f"보고서 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="보고서 조회 중 오류가 발생했습니다.")

@router.get("/reports/{report_id}", response_model=LovebugReport)
async def get_report(report_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    """특정 러브버그 보고서 조회"""
    try:
        from bson import ObjectId
        
        collection = db.lovebug_reports
        doc = await collection.find_one({"_id": ObjectId(report_id)})
        
        if not doc:
            raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")
        
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        
        return LovebugReport(**doc)
        
    except Exception as e:
        logger.error(f"보고서 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="보고서 조회 중 오류가 발생했습니다.")

@router.get("/stats", response_model=LovebugStats)
async def get_stats(
    hours: int = Query(24, ge=1, le=168, description="최근 N시간 내 통계"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """러브버그 통계 정보 조회"""
    try:
        since = datetime.now() - timedelta(hours=hours)
        collection = db.lovebug_reports
        
        # 기본 통계
        total_reports = await collection.count_documents({"created_at": {"$gte": since}})
        
        # 시간대별 통계
        pipeline_hourly = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {
                "_id": {"$hour": "$created_at"},
                "count": {"$sum": 1}
            }}
        ]
        
        reports_by_hour = {}
        async for doc in collection.aggregate(pipeline_hourly):
            reports_by_hour[doc["_id"]] = doc["count"]
        
        # 지역별 통계
        pipeline_district = [
            {"$match": {"created_at": {"$gte": since}, "location.district": {"$exists": True}}},
            {"$group": {
                "_id": "$location.district",
                "count": {"$sum": 1}
            }}
        ]
        
        reports_by_district = {}
        async for doc in collection.aggregate(pipeline_district):
            reports_by_district[doc["_id"]] = doc["count"]
        
        # 심각도별 통계
        pipeline_severity = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {
                "_id": "$severity",
                "count": {"$sum": 1}
            }}
        ]
        
        severity_distribution = {}
        async for doc in collection.aggregate(pipeline_severity):
            severity_distribution[doc["_id"]] = doc["count"]
        
        # 키워드 통계
        pipeline_keywords = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$unwind": "$keywords"},
            {"$group": {
                "_id": "$keywords",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        top_keywords = []
        async for doc in collection.aggregate(pipeline_keywords):
            top_keywords.append({"keyword": doc["_id"], "count": doc["count"]})
        
        # 평균 감정 점수
        pipeline_sentiment = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {
                "_id": None,
                "avg_sentiment": {"$avg": "$sentiment"}
            }}
        ]
        
        average_sentiment = 0.0
        async for doc in collection.aggregate(pipeline_sentiment):
            average_sentiment = doc["avg_sentiment"] or 0.0
        
        return LovebugStats(
            total_reports=total_reports,
            reports_by_hour=reports_by_hour,
            reports_by_district=reports_by_district,
            severity_distribution=severity_distribution,
            top_keywords=top_keywords,
            average_sentiment=average_sentiment,
            last_updated=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"통계 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="통계 조회 중 오류가 발생했습니다.")

@router.get("/hotspots", response_model=List[HotSpot])
async def get_hotspots(
    limit: int = Query(10, ge=1, le=50),
    radius: float = Query(1.0, ge=0.1, le=10.0, description="핫스팟 반경 (km)"),
    hours: int = Query(24, ge=1, le=168, description="최근 N시간 내 데이터"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """러브버그 핫스팟 조회"""
    try:
        since = datetime.now() - timedelta(hours=hours)
        collection = db.lovebug_reports
        
        # 위치 정보가 있는 보고서들을 그룹화
        pipeline = [
            {"$match": {
                "created_at": {"$gte": since},
                "location": {"$exists": True}
            }},
            {"$group": {
                "_id": {
                    "district": "$location.district",
                    "lat": {"$round": ["$location.latitude", 2]},
                    "lng": {"$round": ["$location.longitude", 2]}
                },
                "count": {"$sum": 1},
                "avg_severity": {"$avg": {"$switch": {
                    "branches": [
                        {"case": {"$eq": ["$severity", "low"]}, "then": 1},
                        {"case": {"$eq": ["$severity", "medium"]}, "then": 2},
                        {"case": {"$eq": ["$severity", "high"]}, "then": 3},
                        {"case": {"$eq": ["$severity", "critical"]}, "then": 4}
                    ],
                    "default": 1
                }}},
                "last_activity": {"$max": "$created_at"}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        hotspots = []
        async for doc in collection.aggregate(pipeline):
            if doc["count"] >= 2:  # 최소 2개 이상의 보고서가 있는 경우만
                hotspots.append(HotSpot(
                    location=Location(
                        latitude=doc["_id"]["lat"],
                        longitude=doc["_id"]["lng"],
                        district=doc["_id"]["district"]
                    ),
                    report_count=doc["count"],
                    average_severity=doc["avg_severity"],
                    radius=radius,
                    last_activity=doc["last_activity"]
                ))
        
        return hotspots
        
    except Exception as e:
        logger.error(f"핫스팟 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="핫스팟 조회 중 오류가 발생했습니다.")

@router.get("/search", response_model=List[LovebugReport])
async def search_reports(
    keyword: Optional[str] = Query(None, description="검색 키워드"),
    latitude: Optional[float] = Query(None, description="중심 위도"),
    longitude: Optional[float] = Query(None, description="중심 경도"),
    radius: Optional[float] = Query(None, ge=0.1, le=50.0, description="검색 반경 (km)"),
    severity: Optional[SeverityLevel] = None,
    platform: Optional[Platform] = None,
    hours: Optional[int] = Query(None, ge=1, le=168, description="최근 N시간 내 데이터"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """러브버그 보고서 검색"""
    try:
        query = {}
        
        # 키워드 검색
        if keyword:
            query["$or"] = [
                {"content": {"$regex": keyword, "$options": "i"}},
                {"keywords": {"$in": [keyword]}}
            ]
        
        # 심각도 필터
        if severity:
            query["severity"] = severity.value
        
        # 플랫폼 필터
        if platform:
            query["platform"] = platform.value
        
        # 시간 필터
        if hours:
            since = datetime.now() - timedelta(hours=hours)
            query["created_at"] = {"$gte": since}
        
        # 위치 필터 (간단한 bounding box)
        if latitude and longitude and radius:
            lat_range = radius / 111.0  # 대략적인 위도 변환
            lng_range = radius / (111.0 * abs(latitude))  # 대략적인 경도 변환
            
            query["location.latitude"] = {
                "$gte": latitude - lat_range,
                "$lte": latitude + lat_range
            }
            query["location.longitude"] = {
                "$gte": longitude - lng_range,
                "$lte": longitude + lng_range
            }
        
        collection = db.lovebug_reports
        cursor = collection.find(query).sort("created_at", DESCENDING).limit(limit)
        
        reports = []
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            reports.append(LovebugReport(**doc))
        
        return reports
        
    except Exception as e:
        logger.error(f"보고서 검색 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="보고서 검색 중 오류가 발생했습니다.")

@router.get("/districts", response_model=List[Dict[str, Any]])
async def get_districts(
    hours: int = Query(24, ge=1, le=168, description="최근 N시간 내 데이터"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """지역별 러브버그 현황 조회"""
    try:
        since = datetime.now() - timedelta(hours=hours)
        collection = db.lovebug_reports
        
        pipeline = [
            {"$match": {
                "created_at": {"$gte": since},
                "location.district": {"$exists": True}
            }},
            {"$group": {
                "_id": "$location.district",
                "count": {"$sum": 1},
                "avg_severity": {"$avg": {"$switch": {
                    "branches": [
                        {"case": {"$eq": ["$severity", "low"]}, "then": 1},
                        {"case": {"$eq": ["$severity", "medium"]}, "then": 2},
                        {"case": {"$eq": ["$severity", "high"]}, "then": 3},
                        {"case": {"$eq": ["$severity", "critical"]}, "then": 4}
                    ],
                    "default": 1
                }}},
                "last_activity": {"$max": "$created_at"}
            }},
            {"$sort": {"count": -1}}
        ]
        
        districts = []
        async for doc in collection.aggregate(pipeline):
            districts.append({
                "district": doc["_id"],
                "count": doc["count"],
                "average_severity": doc["avg_severity"],
                "last_activity": doc["last_activity"]
            })
        
        return districts
        
    except Exception as e:
        logger.error(f"지역별 현황 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="지역별 현황 조회 중 오류가 발생했습니다.")