import aiohttp
import asyncio
import os
from typing import Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

class RAGClient:
    def __init__(self):
        self.api_url = os.getenv('RAG_API_URL')
        self.api_key = os.getenv('RAG_API_KEY')
        self.poll_interval = int(os.getenv('RAG_POLL_INTERVAL_SEC', 3))
        self.max_attempts = int(os.getenv('RAG_MAX_ATTEMPTS', 100))
        self.test_mode = os.getenv('RAG_TEST', '').lower() in ['true', '1', 'yes', 'on']
        
        if self.test_mode:
            logger.info("RAG is running in TEST MODE - will return test responses")
            self.test_response = "тестовый ответ [к реальному API не обращался]"
        else:
            if not self.api_url or not self.api_key:
                raise ValueError("RAG_API_URL and RAG_API_KEY environment variables are required")
    
    async def send_request(self, text: str, user_id: int, username: str = None) -> Optional[str]:
        """
        Отправка запроса в RAG API и ожидание ответа
        
        Args:
            text: Текст вопроса
            user_id: ID пользователя
            username: Имя пользователя
            
        Returns:
            Ответ от RAG API или None в случае ошибки
        """
        logger.info(f"Sending RAG request for user {user_id} (@{username}): {text[:100]}...")
        
        try:
            # Если режим тестирования, возвращаем тестовый ответ
            if self.test_mode:
                logger.info(f"Test mode active, returning test response for user {user_id}")
                from database.db import db
                await db.log_rag_request(user_id, "TEST_MODE", text[:200] + "..." if len(text) > 200 else text, 'success')
                return self.test_response
            
            # Отправка запроса
            request_id = await self._create_request(text, user_id, username)
            if not request_id:
                logger.error(f"Failed to create RAG request for user {user_id}")
                return None
            
            logger.debug(f"RAG request created with ID: {request_id}")
            
            # Логируем RAG запрос в базу данных
            from database.db import db
            await db.log_rag_request(user_id, request_id, text[:200] + "..." if len(text) > 200 else text, 'pending')
            
            # Ожидание ответа
            logger.debug(f"Waiting for RAG response for request {request_id}")
            response = await self._wait_for_response(request_id)
            
            if response:
                logger.info(f"RAG response received for user {user_id}, length: {len(response)} chars")
                await db.update_rag_request_status(request_id, 'success')
            else:
                logger.warning(f"No RAG response received for user {user_id}, request {request_id}")
                await db.update_rag_request_status(request_id, 'failed')
            
            return response
            
        except Exception as e:
            logger.error(f"Error in RAG request for user {user_id}: {e}")
            return None
    
    async def _create_request(self, text: str, user_id: int, username: str = None) -> Optional[str]:
        """Создание запроса в RAG API"""
        url = f"{self.api_url}/api/v1/request"
        headers = {
            'ApiKey': self.api_key,
            'Content-Type': 'application/json'
        }
        data = {
            'text': text,
            'dialog_id': str(user_id)
            # 'user_id': int(user_id),
            # 'user_name': username or str(user_id)
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        return result.get('id')
                    else:
                        logger.error(f"RAG API error: {response.status} - {await response.text()}")
                        return None
        except Exception as e:
            logger.error(f"Error creating RAG request: {e}")
            return None
    
    async def _wait_for_response(self, request_id: str) -> Optional[str]:
        """Ожидание ответа от RAG API"""
        url = f"{self.api_url}/api/v1/request/{request_id}"
        headers = {'ApiKey': self.api_key}
        
        for attempt in range(self.max_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            status = result.get('status')
                            
                            if status == 'completed':
                                return result.get('response_text')
                            elif status == 'failed':
                                logger.error(f"RAG request failed: {result}")
                                return None
                            # Если статус 'processing' или другой, продолжаем ждать
                            
                        else:
                            logger.error(f"RAG API error: {response.status} - {await response.text()}")
                            return None
                            
            except Exception as e:
                logger.error(f"Error checking RAG response: {e}")
                return None
            
            # Ждем перед следующей попыткой
            await asyncio.sleep(self.poll_interval)
        
        # Если превышено максимальное количество попыток
        logger.warning(f"RAG request {request_id} timed out after {self.max_attempts} attempts")
        return None

# Глобальный экземпляр RAG клиента
rag_client = RAGClient()
