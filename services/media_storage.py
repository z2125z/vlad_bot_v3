import os
import asyncio
from aiogram import Bot
from aiogram.types import FSInputFile
import aiofiles
from services.logger import logger
import hashlib
import time
from datetime import datetime, timedelta
import json
from typing import Dict, Optional

class MediaStorage:
    def __init__(self, storage_dir: str = "media_storage"):
        self.storage_dir = storage_dir
        self.metadata_file = os.path.join(storage_dir, "metadata.json")
        self._ensure_storage_dir()
        self._load_metadata()
        self.bot = None
        
    def set_bot(self, bot: Bot):
        """Установить бота для скачивания файлов"""
        self.bot = bot
        
    def _ensure_storage_dir(self):
        """Создать директорию для хранения медиа"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            logger.info(f"Created media storage directory: {self.storage_dir}")
            
        # Создаем поддиректории
        for subdir in ['photos', 'videos', 'documents', 'voices', 'video_notes', 'metadata']:
            path = os.path.join(self.storage_dir, subdir)
            if not os.path.exists(path):
                os.makedirs(path)
                
    def _load_metadata(self):
        """Загрузить метаданные файлов"""
        self.metadata: Dict[str, Dict] = {}
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded metadata for {len(self.metadata)} files")
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
                self.metadata = {}
        else:
            self.metadata = {}
            
    def _save_metadata(self):
        """Сохранить метаданные файлов"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def _get_file_hash(self, file_id: str) -> str:
        """Получить хэш файла для имени"""
        return hashlib.md5(file_id.encode()).hexdigest()
    
    def _get_file_path(self, file_id: str, file_type: str) -> str:
        """Получить путь к файлу"""
        hash_name = self._get_file_hash(file_id)
        
        # Определяем расширение в зависимости от типа
        extensions = {
            'photo': '.jpg',
            'video': '.mp4',
            'document': '',  # Будем брать из исходного файла
            'voice': '.ogg',
            'video_note': '.mp4'
        }
        
        ext = extensions.get(file_type, '')
        subdirs = {
            'photo': 'photos',
            'video': 'videos',
            'document': 'documents',
            'voice': 'voices',
            'video_note': 'video_notes'
        }
        
        subdir = subdirs.get(file_type, 'other')
        return os.path.join(self.storage_dir, subdir, f"{hash_name}{ext}")
    
    def _update_file_metadata(self, file_id: str, file_type: str, local_path: str):
        """Обновить метаданные файла"""
        file_hash = self._get_file_hash(file_id)
        current_time = time.time()
        
        if file_hash in self.metadata:
            # Обновляем время последнего использования
            self.metadata[file_hash]['last_used'] = current_time
            self.metadata[file_hash]['use_count'] = self.metadata[file_hash].get('use_count', 0) + 1
        else:
            # Создаем новую запись
            self.metadata[file_hash] = {
                'file_id': file_id,
                'file_type': file_type,
                'local_path': local_path,
                'created_at': current_time,
                'last_used': current_time,
                'use_count': 1,
                'downloaded_at': current_time
            }
        
        self._save_metadata()
    
    async def download_and_store(self, file_id: str, file_type: str) -> str:
        """Скачать и сохранить файл, вернуть путь к локальному файлу"""
        if not self.bot:
            raise ValueError("Bot not set for MediaStorage")
            
        local_path = self._get_file_path(file_id, file_type)
        
        # Если файл уже существует, обновляем метаданные и возвращаем путь
        if os.path.exists(local_path):
            logger.debug(f"File already exists: {local_path}")
            self._update_file_metadata(file_id, file_type, local_path)
            return local_path
            
        try:
            # Скачиваем файл
            file = await self.bot.get_file(file_id)
            file_path = file.file_path
            
            # Скачиваем содержимое
            await self.bot.download_file(file_path, local_path)
            logger.info(f"Downloaded and stored file: {file_id} -> {local_path}")
            
            # Обновляем метаданные
            self._update_file_metadata(file_id, file_type, local_path)
            
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            raise
            
    async def get_file_input(self, file_id: str, file_type: str) -> FSInputFile:
        """Получить FSInputFile для отправки"""
        local_path = await self.download_and_store(file_id, file_type)
        return FSInputFile(local_path)
    
    def cleanup_old_files(self, days_old: int = 180):
        """Очистка старых файлов (по умолчанию 180 дней)"""
        logger.info(f"Starting cleanup of files older than {days_old} days...")
        
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        files_deleted = 0
        files_kept = 0
        
        # Проверяем файлы в метаданных
        file_hashes_to_remove = []
        
        for file_hash, metadata in list(self.metadata.items()):
            local_path = metadata.get('local_path')
            last_used = metadata.get('last_used', 0)
            created_at = metadata.get('created_at', 0)
            
            # Определяем самое старое время для сравнения
            oldest_time = min(last_used, created_at)
            
            if oldest_time < cutoff_time:
                # Удаляем файл, если он существует
                if local_path and os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                        files_deleted += 1
                        logger.debug(f"Deleted old file: {local_path} (last used: {datetime.fromtimestamp(last_used)})")
                    except Exception as e:
                        logger.error(f"Error removing file {local_path}: {e}")
                
                # Помечаем для удаления из метаданных
                file_hashes_to_remove.append(file_hash)
            else:
                files_kept += 1
        
        # Удаляем записи из метаданных
        for file_hash in file_hashes_to_remove:
            if file_hash in self.metadata:
                del self.metadata[file_hash]
        
        # Сохраняем обновленные метаданные
        if file_hashes_to_remove:
            self._save_metadata()
        
        # Также проверяем файлы в директориях, которых нет в метаданных
        for root, dirs, files in os.walk(self.storage_dir):
            # Пропускаем директорию с метаданными
            if 'metadata' in root:
                continue
                
            for file in files:
                # Пропускаем файл метаданных
                if file == 'metadata.json':
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    # Если файл очень старый по времени модификации
                    if os.path.getmtime(file_path) < cutoff_time:
                        # Проверяем, есть ли этот файл в метаданных
                        file_found = False
                        for metadata in self.metadata.values():
                            if metadata.get('local_path') == file_path:
                                file_found = True
                                break
                        
                        # Если файла нет в метаданных или он старый, удаляем
                        if not file_found:
                            os.remove(file_path)
                            files_deleted += 1
                            logger.debug(f"Deleted orphaned file: {file_path}")
                except Exception as e:
                    logger.error(f"Error checking file {file_path}: {e}")
        
        logger.info(f"Cleanup completed. Deleted: {files_deleted}, Kept: {files_kept}")
        
        # Возвращаем статистику для возможного использования
        return {
            'deleted': files_deleted,
            'kept': files_kept,
            'total_metadata': len(self.metadata)
        }
    
    def get_storage_stats(self) -> Dict:
        """Получить статистику хранилища"""
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(self.storage_dir):
            # Пропускаем директорию с метаданными
            if 'metadata' in root:
                continue
                
            for file in files:
                if file == 'metadata.json':
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                    file_count += 1
                except:
                    pass
        
        # Статистика по типам файлов
        file_types = {}
        for metadata in self.metadata.values():
            file_type = metadata.get('file_type', 'unknown')
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        # Возраст самого старого файла
        oldest_file = None
        current_time = time.time()
        for metadata in self.metadata.values():
            created_at = metadata.get('created_at', current_time)
            if oldest_file is None or created_at < oldest_file:
                oldest_file = created_at
        
        oldest_days = 0
        if oldest_file:
            oldest_days = (current_time - oldest_file) / (24 * 60 * 60)
        
        return {
            'total_files': file_count,
            'total_size_mb': total_size / (1024 * 1024),
            'metadata_entries': len(self.metadata),
            'file_types': file_types,
            'oldest_file_days': round(oldest_days, 1),
            'storage_path': self.storage_dir
        }
    
    def force_cleanup_all_unused(self, days_unused: int = 30):
        """Принудительная очистка всех неиспользуемых файлов"""
        logger.warning(f"Force cleaning all files unused for {days_unused} days...")
        
        cutoff_time = time.time() - (days_unused * 24 * 60 * 60)
        files_deleted = 0
        
        # Удаляем файлы, которые не использовались указанное время
        for file_hash, metadata in list(self.metadata.items()):
            last_used = metadata.get('last_used', 0)
            local_path = metadata.get('local_path')
            
            if last_used < cutoff_time and local_path and os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    del self.metadata[file_hash]
                    files_deleted += 1
                    logger.info(f"Force deleted unused file: {local_path}")
                except Exception as e:
                    logger.error(f"Error force deleting file {local_path}: {e}")
        
        self._save_metadata()
        logger.warning(f"Force cleanup completed. Deleted {files_deleted} files.")
        return files_deleted

# Глобальный экземпляр
media_storage = MediaStorage()