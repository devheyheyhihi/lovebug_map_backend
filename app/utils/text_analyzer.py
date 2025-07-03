import re
from typing import Dict, Any, List
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TextAnalyzer:
    """텍스트 분석 클래스"""
    
    def __init__(self):
        # 감정 분석을 위한 키워드 사전
        self.positive_words = ['좋다', '괜찮다', '재미있다', '신기하다', '놀랍다']
        self.negative_words = ['싫다', '짜증', '혐오', '더럽다', '역겹다', '끔찍하다', '최악', '지옥']
        
        # 강도 표현 키워드
        self.intensity_words = {
            'high': ['엄청', '완전', '진짜', '대박', '미친', '떼거리', '지옥'],
            'medium': ['많이', '꽤', '제법', '좀', '조금'],
            'low': ['약간', '살짝', '가끔']
        }
        
        # 위치 패턴
        self.location_patterns = [
            r'([가-힣]+역)\s*에서?',
            r'([가-힣]+구)\s*에서?',
            r'([가-힣]+동)\s*에서?',
            r'([가-힣]+로)\s*에서?',
            r'([가-힣]+거리)\s*에서?',
            r'([가-힣]+공원)\s*에서?',
            r'([가-힣]+대학교?)\s*에서?'
        ]
    
    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """텍스트 종합 분석"""
        try:
            # 기본 정보 추출
            word_count = len(text.split())
            char_count = len(text)
            
            # 감정 분석
            sentiment = self._analyze_sentiment(text)
            
            # 강도 분석
            intensity = self._analyze_intensity(text)
            
            # 키워드 신뢰도 계산
            confidence = self._calculate_confidence(text)
            
            # 러브버그 관련성 점수
            relevance = self._calculate_relevance(text)
            
            return {
                'sentiment': sentiment,
                'intensity': intensity,
                'confidence': confidence,
                'relevance': relevance,
                'word_count': word_count,
                'char_count': char_count,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"텍스트 분석 중 오류: {str(e)}")
            return {
                'sentiment': 0.0,
                'intensity': 'medium',
                'confidence': 0.5,
                'relevance': 0.5,
                'word_count': 0,
                'char_count': 0,
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def _analyze_sentiment(self, text: str) -> float:
        """감정 분석 (-1.0 ~ 1.0)"""
        positive_count = sum(1 for word in self.positive_words if word in text)
        negative_count = sum(1 for word in self.negative_words if word in text)
        
        # 러브버그 관련 텍스트는 대부분 부정적
        total_words = len(text.split())
        
        if total_words == 0:
            return 0.0
        
        # 부정적 키워드가 많으면 부정적 점수
        if negative_count > positive_count:
            return -min(0.8, negative_count / total_words * 5)
        elif positive_count > negative_count:
            return min(0.3, positive_count / total_words * 3)  # 러브버그 맥락에서는 크게 긍정적이지 않음
        else:
            return -0.2  # 기본적으로 약간 부정적
    
    def _analyze_intensity(self, text: str) -> str:
        """강도 분석"""
        text_lower = text.lower()
        
        # 강도별 키워드 매칭
        high_score = sum(1 for word in self.intensity_words['high'] if word in text_lower)
        medium_score = sum(1 for word in self.intensity_words['medium'] if word in text_lower)
        low_score = sum(1 for word in self.intensity_words['low'] if word in text_lower)
        
        if high_score > 0:
            return 'high'
        elif medium_score > 0:
            return 'medium'
        elif low_score > 0:
            return 'low'
        else:
            return 'medium'  # 기본값
    
    def _calculate_confidence(self, text: str) -> float:
        """신뢰도 계산 (0.0 ~ 1.0)"""
        confidence = 0.5  # 기본값
        
        # 러브버그 관련 키워드가 있으면 신뢰도 증가
        lovebug_keywords = ['러브버그', '붉은등우단털파리', '빨간벌레', '차에 붙은']
        keyword_count = sum(1 for keyword in lovebug_keywords if keyword in text)
        confidence += keyword_count * 0.2
        
        # 위치 정보가 있으면 신뢰도 증가
        location_found = any(re.search(pattern, text) for pattern in self.location_patterns)
        if location_found:
            confidence += 0.2
        
        # 시간 정보가 있으면 신뢰도 증가
        time_keywords = ['지금', '오늘', '방금', '현재', '지금껏']
        if any(keyword in text for keyword in time_keywords):
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _calculate_relevance(self, text: str) -> float:
        """러브버그 관련성 점수 (0.0 ~ 1.0)"""
        relevance = 0.0
        
        # 직접적인 러브버그 언급
        direct_keywords = ['러브버그', '붉은등우단털파리']
        for keyword in direct_keywords:
            if keyword in text:
                relevance += 0.4
        
        # 간접적인 언급
        indirect_keywords = ['빨간벌레', '파리', '벌레', '차에 붙은']
        for keyword in indirect_keywords:
            if keyword in text:
                relevance += 0.2
        
        # 상황 키워드
        context_keywords = ['떼', '많아', '붙어', '달라붙']
        for keyword in context_keywords:
            if keyword in text:
                relevance += 0.1
        
        return min(1.0, relevance)
    
    def extract_locations_from_text(self, text: str) -> List[str]:
        """텍스트에서 위치 정보 추출"""
        locations = []
        
        for pattern in self.location_patterns:
            matches = re.findall(pattern, text)
            locations.extend(matches)
        
        return list(set(locations))  # 중복 제거
    
    def extract_keywords(self, text: str) -> List[str]:
        """키워드 추출"""
        keywords = []
        
        # 러브버그 관련 키워드
        lovebug_keywords = ['러브버그', '붉은등우단털파리', '빨간벌레', '벌레', '파리']
        for keyword in lovebug_keywords:
            if keyword in text:
                keywords.append(keyword)
        
        # 위치 키워드
        locations = self.extract_locations_from_text(text)
        keywords.extend(locations)
        
        # 강도 키워드
        for intensity_list in self.intensity_words.values():
            for word in intensity_list:
                if word in text:
                    keywords.append(word)
        
        return list(set(keywords))  # 중복 제거