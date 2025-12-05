import os
import asyncio
from aiogram import Bot
from aiogram.types import FSInputFile
import hashlib
import time
from datetime import datetime
import json
from typing import Dict, Optional, List, Any
import mimetypes
import shutil

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
            os.makedirs(self.storage_dir, exist_ok=True)
            print(f"Created media storage directory: {self.storage_dir}")
            
        # Создаем поддиректории
        for subdir in ['photos', 'videos', 'documents', 'voices', 'video_notes', 'other']:
            path = os.path.join(self.storage_dir, subdir)
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                
    def _load_metadata(self):
        """Загрузить метаданные файлов"""
        self.metadata: Dict[str, Dict] = {}
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                print(f"Loaded metadata for {len(self.metadata)} files")
            except json.JSONDecodeError as e:
                print(f"Error parsing metadata file: {e}. Creating new metadata.")
                self.metadata = {}
                self._save_metadata()
            except Exception as e:
                print(f"Error loading metadata: {e}")
                self.metadata = {}
        else:
            self.metadata = {}
            
    def _save_metadata(self):
        """Сохранить метаданные файлов"""
        try:
            # Создаем временный файл для безопасной записи
            temp_file = self.metadata_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                # Сериализуем данные с обработкой datetime
                serializable_metadata = {}
                for file_hash, metadata in self.metadata.items():
                    serializable_metadata[file_hash] = {}
                    for key, value in metadata.items():
                        if isinstance(value, datetime):
                            serializable_metadata[file_hash][key] = value.isoformat()
                        else:
                            serializable_metadata[file_hash][key] = value
                
                json.dump(serializable_metadata, f, ensure_ascii=False, indent=2)
            
            # Заменяем старый файл новым
            if os.path.exists(self.metadata_file):
                os.remove(self.metadata_file)
            os.rename(temp_file, self.metadata_file)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def _get_file_hash(self, file_id: str) -> str:
        """Получить хэш файла для имени"""
        return hashlib.md5(file_id.encode()).hexdigest()
    
    def _get_original_extension(self, file_name: Optional[str] = None, mime_type: Optional[str] = None) -> str:
        """Получить оригинальное расширение файла"""
        if file_name:
            # Извлекаем расширение из имени файла
            _, ext = os.path.splitext(file_name)
            if ext:
                return ext.lower()
        
        if mime_type:
            # Маппинг MIME типов к расширениям
            mime_to_ext = {
                'image/jpeg': '.jpg',
                'image/jpg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'video/mp4': '.mp4',
                'video/avi': '.avi',
                'video/mov': '.mov',
                'video/mpeg': '.mpeg',
                'application/pdf': '.pdf',
                'application/msword': '.doc',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                'application/vnd.ms-excel': '.xls',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
                'application/zip': '.zip',
                'application/x-rar-compressed': '.rar',
                'audio/mpeg': '.mp3',
                'audio/ogg': '.ogg',
                'audio/wav': '.wav',
                'text/plain': '.txt',
            }
            return mime_to_ext.get(mime_type, '')
        
        return ''
    
    def _sanitize_filename(self, filename: str) -> str:
        """Очистить имя файла от опасных символов"""
        # Удаляем опасные символы
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Ограничиваем длину имени файла
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:95] + ext
        
        return filename
    
    def _get_file_path(self, file_id: str, file_type: str, original_name: Optional[str] = None, mime_type: Optional[str] = None) -> str:
        """Получить путь к файлу с сохранением имени и расширения"""
        file_hash = self._get_file_hash(file_id)
        
        # Определяем поддиректорию по типу
        subdirs = {
            'photo': 'photos',
            'video': 'videos',
            'document': 'documents',
            'voice': 'voices',
            'video_note': 'video_notes'
        }
        
        subdir = subdirs.get(file_type, 'other')
        
        # Если есть оригинальное имя, используем его с хэшем
        if original_name and file_type == 'document':
            # Сохраняем оригинальное имя, но добавляем хэш для уникальности
            name_without_ext, original_ext = os.path.splitext(original_name)
            if not original_ext:
                original_ext = self._get_original_extension(mime_type=mime_type)
            
            # Очищаем имя файла
            safe_name = self._sanitize_filename(name_without_ext)
            filename = f"{safe_name}_{file_hash}{original_ext}"
        else:
            # Для других типов медиа используем стандартные расширения
            default_extensions = {
                'photo': '.jpg',
                'video': '.mp4',
                'document': '.bin',  # Фолбэк для документов
                'voice': '.ogg',
                'video_note': '.mp4'
            }
            ext = default_extensions.get(file_type, '')
            filename = f"{file_hash}{ext}"
        
        return os.path.join(self.storage_dir, subdir, filename)
    
    def _update_file_metadata(self, file_id: str, file_type: str, local_path: str, 
                             original_name: Optional[str] = None, mime_type: Optional[str] = None):
        """Обновить метаданные файла с сохранением оригинальной информации"""
        file_hash = self._get_file_hash(file_id)
        current_time = time.time()
        
        if file_hash in self.metadata:
            # Обновляем время последнего использования
            self.metadata[file_hash]['last_used'] = current_time
            self.metadata[file_hash]['use_count'] = self.metadata[file_hash].get('use_count', 0) + 1
        else:
            # Создаем новую запись с полной информацией
            self.metadata[file_hash] = {
                'file_id': file_id,
                'file_type': file_type,
                'local_path': local_path,
                'original_name': original_name,
                'mime_type': mime_type,
                'created_at': current_time,
                'last_used': current_time,
                'use_count': 1,
                'downloaded_at': current_time
            }
        
        self._save_metadata()
    
    async def download_and_store(self, file_id: str, file_type: str, 
                                original_name: Optional[str] = None, mime_type: Optional[str] = None) -> str:
        """Скачать и сохранить файл, вернуть путь к локальному файлу"""
        if not self.bot:
            raise ValueError("Bot not set for MediaStorage")
            
        local_path = self._get_file_path(file_id, file_type, original_name, mime_type)
        
        # Если файл уже существует, обновляем метаданные и возвращаем путь
        if os.path.exists(local_path):
            print(f"File already exists: {local_path}")
            self._update_file_metadata(file_id, file_type, local_path, original_name, mime_type)
            return local_path
            
        try:
            # Скачиваем файл
            file = await self.bot.get_file(file_id)
            file_path = file.file_path
            
            if not file_path:
                raise ValueError(f"File path not found for file_id: {file_id}")
            
            # Создаем директорию если её нет
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Скачиваем содержимое
            await self.bot.download_file(file_path, local_path)
            
            print(f"Downloaded and stored file: {file_id}")
            print(f"  Original name: {original_name or 'N/A'}")
            print(f"  Saved as: {os.path.basename(local_path)}")
            print(f"  Path: {local_path}")
            
            # Обновляем метаданные
            self._update_file_metadata(file_id, file_type, local_path, original_name, mime_type)
            
            return local_path
            
        except Exception as e:
            print(f"Error downloading file {file_id}: {e}")
            # Удаляем частично скачанный файл
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except:
                    pass
            raise
            
    async def get_file_input(self, file_id: str, file_type: str, 
                            original_name: Optional[str] = None, mime_type: Optional[str] = None) -> FSInputFile:
        """Получить FSInputFile для отправки с сохранением имени"""
        local_path = await self.download_and_store(file_id, file_type, original_name, mime_type)
        
        # Для документов устанавливаем оригинальное имя файла
        if file_type == 'document' and original_name:
            return FSInputFile(local_path, filename=original_name)
        
        return FSInputFile(local_path)
    
    def cleanup_old_files(self, days_old: int = 180) -> Dict[str, int]:
        """Очистка старых файлов (по умолчанию 180 дней)"""
        print(f"Starting cleanup of files older than {days_old} days...")
        
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
                        original_name = metadata.get('original_name', 'unknown')
                        print(f"Deleted old file: {original_name}")
                    except Exception as e:
                        print(f"Error removing file {local_path}: {e}")
                
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
        
        print(f"Cleanup completed. Deleted: {files_deleted}, Kept: {files_kept}")
        
        return {
            'deleted': files_deleted,
            'kept': files_kept,
            'total_metadata': len(self.metadata)
        }
    
    def force_cleanup_all_unused(self, days_unused: int = 30) -> int:
        """Принудительная очистка всех неиспользуемых файлов"""
        print(f"Force cleanup of all files unused for {days_unused} days...")
        
        cutoff_time = time.time() - (days_unused * 24 * 60 * 60)
        deleted_count = 0
        
        # Удаляем все файлы, которые не использовались указанное время
        for file_hash, metadata in list(self.metadata.items()):
            last_used = metadata.get('last_used', 0)
            local_path = metadata.get('local_path')
            
            if last_used < cutoff_time and local_path and os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    deleted_count += 1
                    print(f"Force deleted file: {metadata.get('original_name', 'unknown')}")
                except Exception as e:
                    print(f"Error force removing file {local_path}: {e}")
        
        # Очищаем метаданные
        self.metadata = {k: v for k, v in self.metadata.items() 
                        if v.get('last_used', 0) >= cutoff_time}
        
        self._save_metadata()
        
        print(f"Force cleanup completed. Deleted: {deleted_count} files")
        return deleted_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Получить статистику хранилища"""
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(self.storage_dir):
            for file in files:
                if file == 'metadata.json' or file.endswith('.tmp'):
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                    file_count += 1
                except (OSError, FileNotFoundError):
                    pass
        
        # Статистика по типам файлов
        file_types: Dict[str, int] = {}
        for metadata in self.metadata.values():
            file_type = metadata.get('file_type', 'unknown')
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        # Статистика по расширениям
        extensions: Dict[str, int] = {}
        for metadata in self.metadata.values():
            original_name = metadata.get('original_name')
            if original_name:
                _, ext = os.path.splitext(original_name)
                if ext:
                    extensions[ext.lower()] = extensions.get(ext.lower(), 0) + 1
        
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
            'extensions': extensions,
            'oldest_file_days': round(oldest_days, 1),
            'storage_path': os.path.abspath(self.storage_dir)
        }
    
    def clear_all_files(self) -> Dict[str, int]:
        """Очистить все файлы и метаданные (опасно!)"""
        print("WARNING: Clearing all media storage files!")
        
        deleted_count = 0
        error_count = 0
        
        # Удаляем все файлы в поддиректориях
        for root, dirs, files in os.walk(self.storage_dir):
            for file in files:
                if file == 'metadata.json':
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"Error removing file {file_path}: {e}")
                    error_count += 1
        
        # Очищаем метаданные
        self.metadata = {}
        self._save_metadata()
        
        print(f"Cleared {deleted_count} files, {error_count} errors")
        
        return {
            'deleted': deleted_count,
            'errors': error_count
        }
    
    def find_file_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Найти файл по хэшу"""
        return self.metadata.get(file_hash)
    
    def find_file_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Найти файл по file_id"""
        file_hash = self._get_file_hash(file_id)
        return self.metadata.get(file_hash)

# Глобальный экземпляр
media_storage = MediaStorage()