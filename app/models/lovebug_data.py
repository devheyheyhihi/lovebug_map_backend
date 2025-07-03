from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class SeverityLevel(str, Enum):
    """심각도 레벨"""
    LOW = "low"          # 적음
    MEDIUM = "medium"    # 보통
    HIGH = "high"        # 많음
    CRITICAL = "critical" # 매우 많음

class Platform(str, Enum):
    """SNS 플랫폼 타입"""
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    NAVER_BLOG = "naver_blog"
    KAKAO_TALK = "kakao_talk"

class Location(BaseModel):
    """위치 정보"""
    latitude: float = Field(..., description="위도")
    longitude: float = Field(..., description="경도")
    address: Optional[str] = Field(None, description="주소")
    district: Optional[str] = Field(None, description="구/군")
    city: Optional[str] = Field(None, description="시/도")

class LovebugReport(BaseModel):
    """러브버그 보고서 모델"""
    id: Optional[str] = Field(None, description="MongoDB ObjectId")
    tweet_id: Optional[str] = Field(None, description="트위터 고유 ID")
    platform: Platform = Field(..., description="플랫폼")
    content: str = Field(..., description="원본 텍스트")
    location: Optional[Location] = Field(None, description="위치 정보")
    severity: SeverityLevel = Field(SeverityLevel.LOW, description="심각도")
    confidence: float = Field(0.0, description="신뢰도 점수 (0.0-1.0)")
    sentiment: float = Field(0.0, description="감정 점수 (-1.0 ~ 1.0)")
    keywords: List[str] = Field(default_factory=list, description="추출된 키워드")
    image_urls: List[str] = Field(default_factory=list, description="이미지 URL")
    author: Optional[str] = Field(None, description="작성자")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")
    updated_at: datetime = Field(default_factory=datetime.now, description="업데이트 시간")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class LovebugStats(BaseModel):
    """러브버그 통계 모델"""
    total_reports: int = Field(0, description="전체 보고서 수")
    reports_by_hour: Dict[int, int] = Field(default_factory=dict, description="시간대별 보고서 수")
    reports_by_district: Dict[str, int] = Field(default_factory=dict, description="지역별 보고서 수")
    severity_distribution: Dict[SeverityLevel, int] = Field(default_factory=dict, description="심각도별 분포")
    top_keywords: List[Dict[str, Any]] = Field(default_factory=list, description="인기 키워드")
    average_sentiment: float = Field(0.0, description="평균 감정 점수")
    last_updated: datetime = Field(default_factory=datetime.now, description="마지막 업데이트")

class HotSpot(BaseModel):
    """러브버그 핫스팟 모델"""
    location: Location = Field(..., description="위치")
    report_count: int = Field(0, description="보고서 수")
    average_severity: float = Field(0.0, description="평균 심각도")
    radius: float = Field(1.0, description="반경 (km)")
    last_activity: datetime = Field(default_factory=datetime.now, description="마지막 활동")

class SearchFilter(BaseModel):
    """검색 필터 모델"""
    start_date: Optional[datetime] = Field(None, description="시작 날짜")
    end_date: Optional[datetime] = Field(None, description="종료 날짜")
    min_severity: Optional[SeverityLevel] = Field(None, description="최소 심각도")
    max_severity: Optional[SeverityLevel] = Field(None, description="최대 심각도")
    platforms: Optional[List[Platform]] = Field(None, description="플랫폼 필터")
    location_radius: Optional[float] = Field(None, description="위치 반경 (km)")
    center_lat: Optional[float] = Field(None, description="중심 위도")
    center_lng: Optional[float] = Field(None, description="중심 경도")
    keywords: Optional[List[str]] = Field(None, description="키워드 필터")
    min_confidence: Optional[float] = Field(None, description="최소 신뢰도")

class RealTimeUpdate(BaseModel):
    """실시간 업데이트 모델"""
    type: str = Field(..., description="업데이트 타입")
    data: Dict[str, Any] = Field(..., description="업데이트 데이터")
    timestamp: datetime = Field(default_factory=datetime.now, description="타임스탬프")