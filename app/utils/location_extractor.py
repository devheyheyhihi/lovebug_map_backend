import re
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
import logging
from app.models.lovebug_data import Location

logger = logging.getLogger(__name__)

class LocationExtractor:
    """위치 추출 및 좌표 변환 클래스"""
    
    def __init__(self):
        # 주요 지역 좌표 매핑 (서울 중심)
        self.location_mapping = {
            # 서울 주요 역/지역
            '강남역': {'lat': 37.4979, 'lng': 127.0276, 'address': '서울특별시 강남구 강남대로 지하396'},
            '홍대': {'lat': 37.5516, 'lng': 126.9226, 'address': '서울특별시 마포구 홍익로'},
            '홍대입구역': {'lat': 37.5516, 'lng': 126.9226, 'address': '서울특별시 마포구 홍익로'},
            '신촌': {'lat': 37.5596, 'lng': 126.9361, 'address': '서울특별시 서대문구 신촌동'},
            '신촌역': {'lat': 37.5596, 'lng': 126.9361, 'address': '서울특별시 서대문구 신촌동'},
            '명동': {'lat': 37.5636, 'lng': 126.9826, 'address': '서울특별시 중구 명동'},
            '명동역': {'lat': 37.5636, 'lng': 126.9826, 'address': '서울특별시 중구 명동'},
            '종로': {'lat': 37.5704, 'lng': 126.9826, 'address': '서울특별시 종로구 종로'},
            '종로3가역': {'lat': 37.5704, 'lng': 126.9826, 'address': '서울특별시 종로구 종로'},
            '이태원': {'lat': 37.5346, 'lng': 126.9942, 'address': '서울특별시 용산구 이태원동'},
            '이태원역': {'lat': 37.5346, 'lng': 126.9942, 'address': '서울특별시 용산구 이태원동'},
            '잠실': {'lat': 37.5134, 'lng': 127.1000, 'address': '서울특별시 송파구 잠실동'},
            '잠실역': {'lat': 37.5134, 'lng': 127.1000, 'address': '서울특별시 송파구 잠실동'},
            '건대': {'lat': 37.5404, 'lng': 127.0696, 'address': '서울특별시 광진구 화양동'},
            '건대입구역': {'lat': 37.5404, 'lng': 127.0696, 'address': '서울특별시 광진구 화양동'},
            '노원': {'lat': 37.6547, 'lng': 127.0613, 'address': '서울특별시 노원구'},
            '노원역': {'lat': 37.6547, 'lng': 127.0613, 'address': '서울특별시 노원구'},
            '수원': {'lat': 37.2636, 'lng': 127.0286, 'address': '경기도 수원시'},
            '수원역': {'lat': 37.2636, 'lng': 127.0286, 'address': '경기도 수원시'},
            '인천': {'lat': 37.4563, 'lng': 126.7052, 'address': '인천광역시'},
            '인천역': {'lat': 37.4563, 'lng': 126.7052, 'address': '인천광역시'},
            # 서울 구별 중심점
            '강남구': {'lat': 37.5172, 'lng': 127.0473, 'address': '서울특별시 강남구'},
            '서초구': {'lat': 37.4836, 'lng': 127.0327, 'address': '서울특별시 서초구'},
            '송파구': {'lat': 37.5145, 'lng': 127.1065, 'address': '서울특별시 송파구'},
            '강동구': {'lat': 37.5301, 'lng': 127.1238, 'address': '서울특별시 강동구'},
            '마포구': {'lat': 37.5663, 'lng': 126.9019, 'address': '서울특별시 마포구'},
            '영등포구': {'lat': 37.5264, 'lng': 126.8962, 'address': '서울특별시 영등포구'},
            '용산구': {'lat': 37.5384, 'lng': 126.9646, 'address': '서울특별시 용산구'},
            '성동구': {'lat': 37.5634, 'lng': 127.0367, 'address': '서울특별시 성동구'},
            '광진구': {'lat': 37.5481, 'lng': 127.0857, 'address': '서울특별시 광진구'},
            '동대문구': {'lat': 37.5838, 'lng': 127.0507, 'address': '서울특별시 동대문구'},
            '중랑구': {'lat': 37.6066, 'lng': 127.0925, 'address': '서울특별시 중랑구'},
            '성북구': {'lat': 37.6066, 'lng': 127.0181, 'address': '서울특별시 성북구'},
            '강북구': {'lat': 37.6398, 'lng': 127.0256, 'address': '서울특별시 강북구'},
            '도봉구': {'lat': 37.6687, 'lng': 127.0471, 'address': '서울특별시 도봉구'},
            '노원구': {'lat': 37.6542, 'lng': 127.0568, 'address': '서울특별시 노원구'},
            '은평구': {'lat': 37.6177, 'lng': 126.9227, 'address': '서울특별시 은평구'},
            '서대문구': {'lat': 37.5791, 'lng': 126.9368, 'address': '서울특별시 서대문구'},
            '종로구': {'lat': 37.5729, 'lng': 126.9792, 'address': '서울특별시 종로구'},
            '중구': {'lat': 37.5637, 'lng': 126.9975, 'address': '서울특별시 중구'},
            '관악구': {'lat': 37.4784, 'lng': 126.9516, 'address': '서울특별시 관악구'},
            '동작구': {'lat': 37.5125, 'lng': 126.9399, 'address': '서울특별시 동작구'},
            '금천구': {'lat': 37.4569, 'lng': 126.8955, 'address': '서울특별시 금천구'},
            '구로구': {'lat': 37.4955, 'lng': 126.8875, 'address': '서울특별시 구로구'},
            '양천구': {'lat': 37.5170, 'lng': 126.8664, 'address': '서울특별시 양천구'},
            '강서구': {'lat': 37.5510, 'lng': 126.8495, 'address': '서울특별시 강서구'}
        }
        
        # 위치 추출 패턴
        self.location_patterns = [
            r'([가-힣]+역)\s*(?:에서?|근처|앞)',
            r'([가-힣]+구)\s*(?:에서?|근처|일대)',
            r'([가-힣]+동)\s*(?:에서?|근처)',
            r'([가-힣]+로)\s*(?:에서?|근처)',
            r'([가-힣]+거리)\s*(?:에서?|근처)',
            r'([가-힣]+공원)\s*(?:에서?|근처)',
            r'([가-힣]+대학교?)\s*(?:에서?|근처|앞)',
            r'([가-힣]+시장)\s*(?:에서?|근처)',
            r'([가-힣]+병원)\s*(?:에서?|근처|앞)'
        ]
    
    async def extract_location(self, text: str) -> Optional[Location]:
        """텍스트에서 위치 정보 추출"""
        try:
            # 직접 매핑된 위치 확인
            for location_name, coords in self.location_mapping.items():
                if location_name in text:
                    return Location(
                        latitude=coords['lat'],
                        longitude=coords['lng'],
                        address=coords['address'],
                        district=self._extract_district(coords['address']),
                        city=self._extract_city(coords['address'])
                    )
            
            # 패턴 매칭으로 위치 추출
            locations = self._extract_location_names(text)
            if locations:
                # 첫 번째 위치를 기준으로 좌표 추정
                location_name = locations[0]
                coords = await self._get_coordinates(location_name)
                if coords:
                    return Location(
                        latitude=coords['lat'],
                        longitude=coords['lng'],
                        address=coords.get('address', location_name),
                        district=self._extract_district(coords.get('address', '')),
                        city=self._extract_city(coords.get('address', ''))
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"위치 추출 중 오류: {str(e)}")
            return None
    
    def _extract_location_names(self, text: str) -> List[str]:
        """패턴 매칭으로 위치명 추출"""
        locations = []
        
        for pattern in self.location_patterns:
            matches = re.findall(pattern, text)
            locations.extend(matches)
        
        return list(set(locations))  # 중복 제거
    
    async def _get_coordinates(self, location_name: str) -> Optional[Dict[str, Any]]:
        """위치명을 좌표로 변환 (카카오 지도 API 또는 추정)"""
        try:
            # 먼저 기본 매핑에서 확인
            if location_name in self.location_mapping:
                return self.location_mapping[location_name]
            
            # 서울 내 주요 지역 추정
            if any(suffix in location_name for suffix in ['역', '구', '동']):
                # 서울 시내 임의 좌표로 추정 (실제로는 외부 API 사용)
                return {
                    'lat': 37.5665 + (hash(location_name) % 1000) / 10000,  # 서울 중심 근처
                    'lng': 126.9780 + (hash(location_name) % 1000) / 10000,
                    'address': f'서울특별시 {location_name}'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"좌표 변환 중 오류: {str(e)}")
            return None
    
    def _extract_district(self, address: str) -> Optional[str]:
        """주소에서 구/군 추출"""
        if not address:
            return None
        
        # 구/군 패턴 매칭
        district_pattern = r'([가-힣]+구|[가-힣]+군)'
        match = re.search(district_pattern, address)
        return match.group(1) if match else None
    
    def _extract_city(self, address: str) -> Optional[str]:
        """주소에서 시/도 추출"""
        if not address:
            return None
        
        # 시/도 패턴 매칭
        city_pattern = r'([가-힣]+시|[가-힣]+도|[가-힣]+특별시|[가-힣]+광역시)'
        match = re.search(city_pattern, address)
        return match.group(1) if match else None
    
    async def get_nearby_locations(self, latitude: float, longitude: float, radius: float = 1.0) -> List[str]:
        """주변 지역 검색"""
        nearby = []
        
        for location_name, coords in self.location_mapping.items():
            # 간단한 거리 계산 (정확하지 않음, 실제로는 haversine 공식 사용)
            lat_diff = abs(coords['lat'] - latitude)
            lng_diff = abs(coords['lng'] - longitude)
            distance = (lat_diff**2 + lng_diff**2)**0.5
            
            if distance <= radius / 100:  # 대략적인 거리 비교
                nearby.append(location_name)
        
        return nearby