from typing import List, Dict, Any
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    """웹소켓 연결 관리 클래스"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str = None):
        """웹소켓 연결 수락"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            'user_id': user_id,
            'connected_at': None,
            'last_activity': None
        }
        logger.info(f"웹소켓 연결 수락: {user_id or 'anonymous'}")
    
    def disconnect(self, websocket: WebSocket):
        """웹소켓 연결 해제"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            user_info = self.connection_info.pop(websocket, {})
            logger.info(f"웹소켓 연결 해제: {user_info.get('user_id', 'anonymous')}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """개별 클라이언트에게 메시지 전송"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"개별 메시지 전송 실패: {str(e)}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """모든 연결된 클라이언트에게 메시지 전송"""
        if not self.active_connections:
            return
        
        disconnected_connections = []
        message_str = json.dumps(message, ensure_ascii=False)
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"브로드캐스트 전송 실패: {str(e)}")
                disconnected_connections.append(connection)
        
        # 연결 실패한 클라이언트들 제거
        for connection in disconnected_connections:
            self.disconnect(connection)
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """특정 사용자에게 메시지 전송"""
        for connection, info in self.connection_info.items():
            if info.get('user_id') == user_id:
                await self.send_personal_message(message, connection)
                return True
        return False
    
    def get_connection_count(self) -> int:
        """현재 연결된 클라이언트 수 반환"""
        return len(self.active_connections)
    
    def get_connected_users(self) -> List[str]:
        """연결된 사용자 ID 목록 반환"""
        return [info.get('user_id') for info in self.connection_info.values() if info.get('user_id')]