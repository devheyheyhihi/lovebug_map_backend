#!/usr/bin/env python3
"""
테스트 데이터 추가 스크립트
"""
import asyncio
import os
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from app.models.lovebug_data import LovebugReport, SeverityLevel, Platform, Location
import random

# 서울 지역 좌표
SEOUL_LOCATIONS = [
    {"name": "강남구", "lat": 37.5172, "lng": 127.0473, "district": "강남구"},
    {"name": "서초구", "lat": 37.4837, "lng": 127.0324, "district": "서초구"},
    {"name": "송파구", "lat": 37.5145, "lng": 127.1065, "district": "송파구"},
    {"name": "마포구", "lat": 37.5663, "lng": 126.9019, "district": "마포구"},
    {"name": "용산구", "lat": 37.5384, "lng": 126.9654, "district": "용산구"},
    {"name": "중구", "lat": 37.5641, "lng": 126.9979, "district": "중구"},
    {"name": "종로구", "lat": 37.5735, "lng": 126.9788, "district": "종로구"},
    {"name": "성동구", "lat": 37.5636, "lng": 127.0366, "district": "성동구"},
    {"name": "광진구", "lat": 37.5384, "lng": 127.0822, "district": "광진구"},
    {"name": "동대문구", "lat": 37.5744, "lng": 127.0396, "district": "동대문구"},
]

# 테스트 메시지 템플릿
TEST_MESSAGES = [
    "러브버그가 너무 많아요 😱 공원에서 산책하기 힘들어요",
    "오늘 아침에 러브버그 떼를 만났어요. 정말 깜짝 놀랐네요!",
    "러브버그 때문에 창문을 열 수가 없어요 ㅠㅠ",
    "산책로에 러브버그가 엄청 많네요. 조심하세요!",
    "러브버그 시즌이 시작된 것 같아요. 외출 시 주의하세요",
    "공원 벤치에 앉을 수가 없을 정도로 러브버그가 많아요",
    "러브버그 때문에 빨래를 밖에 널기 힘들어요",
    "오늘 러브버그 상황이 심각해요. 마스크 착용 필수!",
    "러브버그가 차에 달라붙어서 운전이 힘들어요",
    "공원에서 러브버그 떼를 피해 다니고 있어요",
]

async def add_test_data():
    """테스트 데이터 추가"""
    # MongoDB 연결
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.lovebug_map
    collection = db.lovebug_reports
    
    print("테스트 데이터 추가 시작...")
    
    # 기존 데이터 삭제
    await collection.delete_many({})
    print("기존 데이터 삭제 완료")
    
    # 테스트 데이터 생성
    test_reports = []
    
    for i in range(50):  # 50개의 테스트 데이터
        location_data = random.choice(SEOUL_LOCATIONS)
        
        # 좌표에 약간의 랜덤성 추가
        lat = location_data["lat"] + random.uniform(-0.01, 0.01)
        lng = location_data["lng"] + random.uniform(-0.01, 0.01)
        
        # 랜덤 시간 생성 (최근 72시간 내)
        hours_ago = random.randint(1, 72)
        created_at = datetime.now() - timedelta(hours=hours_ago)
        
        report = LovebugReport(
            id=f"test_{i+1}",
            tweet_id=f"tweet_{i+1}",
            content=random.choice(TEST_MESSAGES),
            author="테스트사용자" + str(i+1),
            created_at=created_at,
            location=Location(
                latitude=lat,
                longitude=lng,
                address=f"{location_data['name']} 일대",
                district=location_data["district"]
            ),
            severity=random.choice(list(SeverityLevel)),
            platform=random.choice(list(Platform)),
            keywords=["러브버그", "벌레", "곤충"] + random.sample(["공원", "산책", "외출", "주의", "많음"], 2),
            sentiment=random.uniform(-1.0, 1.0),
            image_urls=[],
            hashtags=["#러브버그", "#벌레주의"],
            likes=random.randint(0, 100),
            retweets=random.randint(0, 50),
            replies=random.randint(0, 20)
        )
        
        test_reports.append(report.dict())
    
    # 데이터베이스에 삽입
    await collection.insert_many(test_reports)
    print(f"{len(test_reports)}개의 테스트 데이터 추가 완료")
    
    # 통계 확인
    total_count = await collection.count_documents({})
    print(f"총 데이터 개수: {total_count}")
    
    # 지역별 통계
    pipeline = [
        {"$group": {"_id": "$location.district", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    print("\n지역별 통계:")
    async for doc in collection.aggregate(pipeline):
        print(f"  {doc['_id']}: {doc['count']}개")
    
    # 심각도별 통계
    pipeline = [
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    print("\n심각도별 통계:")
    async for doc in collection.aggregate(pipeline):
        print(f"  {doc['_id']}: {doc['count']}개")
    
    await client.close()
    print("\n테스트 데이터 추가 완료!")

if __name__ == "__main__":
    asyncio.run(add_test_data()) 