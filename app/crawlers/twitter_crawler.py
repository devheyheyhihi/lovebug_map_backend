import asyncio
import aiohttp
import tweepy
from bs4 import BeautifulSoup
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import os
from dataclasses import dataclass

from app.models.lovebug_data import LovebugReport, Platform, SeverityLevel, Location
from app.utils.text_analyzer import TextAnalyzer
from app.utils.location_extractor import LocationExtractor

logger = logging.getLogger(__name__)

@dataclass
class TweetData:
    """트위터 데이터 구조"""
    id: str
    text: str
    author: str
    created_at: datetime
    images: List[str]
    location: Optional[str] = None

class TwitterCrawler:
    """트위터 크롤러 클래스"""
    
    def __init__(self):
        self.text_analyzer = TextAnalyzer()
        self.location_extractor = LocationExtractor()
        
        # 러브버그 관련 키워드
        self.lovebug_keywords = [
            "러브버그", "붉은등우단털파리", "서울 벌레", "빨간벌레",
            "차에 붙은 벌레", "파리 떼", "벌레 많아", "벌레 지옥",
            "플레인 파리", "러브버그 습격", "벌레 떼거리"
        ]
        
        # 트위터 API 설정 (환경변수에서 읽기)
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            logger.warning("트위터 API 토큰이 설정되지 않았습니다. 웹 스크래핑 모드로 실행됩니다.")
    
    async def crawl_lovebug_tweets(self) -> List[LovebugReport]:
        """러브버그 관련 트윗 크롤링"""
        reports = []
        
        try:
            if self.bearer_token:
                # 공식 API 사용
                tweets = await self._crawl_with_api()
            else:
                # 웹 스크래핑 사용 (제한적)
                tweets = await self._crawl_with_scraping()
            
            # 각 트윗을 분석하여 LovebugReport로 변환
            for tweet_data in tweets:
                report = await self._process_tweet(tweet_data)
                if report:
                    reports.append(report)
            
            logger.info(f"총 {len(reports)}개의 러브버그 보고서 생성됨")
            return reports
            
        except Exception as e:
            logger.error(f"트위터 크롤링 중 오류 발생: {str(e)}")
            return []
    
    async def _crawl_with_api(self) -> List[TweetData]:
        """트위터 API를 사용한 크롤링"""
        tweets = []
        
        try:
            # Tweepy 클라이언트 설정
            client = tweepy.Client(bearer_token=self.bearer_token)
            
            # 각 키워드로 검색
            for keyword in self.lovebug_keywords:
                try:
                    # 최근 24시간 내 트윗 검색
                    since_time = datetime.now() - timedelta(hours=24)
                    
                    response = client.search_recent_tweets(
                        query=f"{keyword} -is:retweet lang:ko",
                        max_results=10,
                        tweet_fields=['created_at', 'author_id', 'geo', 'attachments'],
                        user_fields=['username'],
                        expansions=['author_id', 'attachments.media_keys'],
                        media_fields=['url'],
                        start_time=since_time
                    )
                    
                    if response.data:
                        for tweet in response.data:
                            # 사용자 정보 찾기
                            author = "Unknown"
                            if response.includes and 'users' in response.includes:
                                for user in response.includes['users']:
                                    if user.id == tweet.author_id:
                                        author = user.username
                                        break
                            
                            # 이미지 URL 추출
                            images = []
                            if hasattr(tweet, 'attachments') and tweet.attachments:
                                if 'media_keys' in tweet.attachments:
                                    if response.includes and 'media' in response.includes:
                                        for media in response.includes['media']:
                                            if media.media_key in tweet.attachments['media_keys']:
                                                if hasattr(media, 'url'):
                                                    images.append(media.url)
                            
                            tweet_data = TweetData(
                                id=tweet.id,
                                text=tweet.text,
                                author=author,
                                created_at=tweet.created_at,
                                images=images,
                                location=getattr(tweet, 'geo', None)
                            )
                            tweets.append(tweet_data)
                    
                    # API 호출 제한을 위한 딜레이
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"키워드 '{keyword}' 검색 중 오류: {str(e)}")
                    continue
            
            return tweets
            
        except Exception as e:
            logger.error(f"트위터 API 크롤링 오류: {str(e)}")
            return []
    
    async def _crawl_with_scraping(self) -> List[TweetData]:
        """웹 스크래핑을 통한 크롤링 (제한적)"""
        tweets = []
        
        try:
            # 네이버 실시간 검색이나 다른 소스에서 데이터 수집
            # 이 부분은 실제 구현에서는 더 정교한 스크래핑이 필요
            
            # 임시로 샘플 데이터 생성 (실제 환경에서는 제거)
            sample_tweets = [
                {
                    "id": "sample_1",
                    "text": "강남역에서 러브버그 진짜 많네요... 차에 다 붙어있어요 ㅠㅠ",
                    "author": "sample_user1",
                    "created_at": datetime.now() - timedelta(minutes=30),
                    "images": []
                },
                {
                    "id": "sample_2", 
                    "text": "홍대 근처에 붉은등우단털파리 떼가 있어요. 조심하세요!",
                    "author": "sample_user2",
                    "created_at": datetime.now() - timedelta(minutes=15),
                    "images": []
                }
            ]
            
            for tweet in sample_tweets:
                tweet_data = TweetData(
                    id=tweet["id"],
                    text=tweet["text"],
                    author=tweet["author"],
                    created_at=tweet["created_at"],
                    images=tweet["images"]
                )
                tweets.append(tweet_data)
            
            return tweets
            
        except Exception as e:
            logger.error(f"웹 스크래핑 오류: {str(e)}")
            return []
    
    async def _process_tweet(self, tweet_data: TweetData) -> Optional[LovebugReport]:
        """트윗 데이터를 LovebugReport로 변환"""
        try:
            # 텍스트 분석
            analysis = await self.text_analyzer.analyze_text(tweet_data.text)
            
            # 위치 추출
            location = await self.location_extractor.extract_location(tweet_data.text)
            
            # 심각도 판단
            severity = self._determine_severity(tweet_data.text, analysis)
            
            # 키워드 추출
            keywords = self._extract_keywords(tweet_data.text)
            
            report = LovebugReport(
                tweet_id=tweet_data.id,
                platform=Platform.TWITTER,
                content=tweet_data.text,
                location=location,
                severity=severity,
                confidence=analysis.get('confidence', 0.7),
                sentiment=analysis.get('sentiment', 0.0),
                keywords=keywords,
                image_urls=tweet_data.images,
                author=tweet_data.author,
                created_at=tweet_data.created_at,
                updated_at=datetime.now()
            )
            
            return report
            
        except Exception as e:
            logger.error(f"트윗 처리 중 오류 발생: {str(e)}")
            return None
    
    def _determine_severity(self, text: str, analysis: Dict[str, Any]) -> SeverityLevel:
        """텍스트 내용을 바탕으로 심각도 판단"""
        text_lower = text.lower()
        
        # 키워드 기반 심각도 판단
        if any(word in text_lower for word in ['지옥', '떼거리', '엄청', '미친', '완전']):
            return SeverityLevel.CRITICAL
        elif any(word in text_lower for word in ['많아', '진짜', '심해', '대박']):
            return SeverityLevel.HIGH
        elif any(word in text_lower for word in ['좀', '꽤', '조금']):
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW
    
    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        keywords = []
        
        # 기본 러브버그 키워드 확인
        for keyword in self.lovebug_keywords:
            if keyword in text:
                keywords.append(keyword)
        
        # 위치 관련 키워드 추출
        location_patterns = [
            r'([가-힣]+역)', r'([가-힣]+구)', r'([가-힣]+동)', 
            r'([가-힣]+로)', r'([가-힣]+거리)'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)
        
        return list(set(keywords))  # 중복 제거