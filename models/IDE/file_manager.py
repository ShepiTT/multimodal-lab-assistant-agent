"""
文件管理系统
处理 IDE 中的文件和文件夹操作
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re


class FileManager:
    """IDE 文件管理器"""
    
    # 支持的文件扩展名和对应的语言
    LANGUAGE_EXTENSIONS = {
        'python': ['.py'],
        'javascript': ['.js', '.mjs'],
        'typescript': ['.ts'],
        'java': ['.java'],
        'c': ['.c', '.h'],
        'cpp': ['.cpp', '.hpp', '.cc', '.cxx', '.h'],
        'go': ['.go'],
        'rust': ['.rs'],
        'html': ['.html', '.htm'],
        'css': ['.css'],
        'json': ['.json'],
        'xml': ['.xml'],
        'markdown': ['.md'],
        'text': ['.txt']
    }
    
    # 文件大小限制（字节）
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    # 会话配额限制（字节）
    SESSION_QUOTA = 50 * 1024 * 1024  # 50MB
    
    def __init__(self, base_dir: str):
        """
        初始化文件管理器
        
        Args:
            base_dir: IDE 会话的基础目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.base_dir / 'files.json'
        self._load_metadata()
    
    def _load_metadata(self):
        """加载文件元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                print(f"加载元数据失败: {e}")
                self.metadata = {'files': {}, 'folders': []}
        else:
            self.metadata = {'files': {}, 'folders': []}
    
    def _save_metadata(self):
        """保存文件元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存元数据失败: {e}")
    
    def _validate_filename(self, filename: str) -> Tuple[bool, str]:
        """
        验证文件名是否合法
        
        Args:
            filename: 文件名
        
        Returns:
            (是否合法, 错误消息)
        """
        if not filename:
            return False, "文件名不能为空"
        
        # 检查危险字符
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in filename:
                return False, f"文件名包含非法字符: {char}"
        
        # 检查文件名长度
        if len(filename) > 255:
            return False, "文件名过长（最多255字符）"
        
        return True, ""
    
    def _get_language_from_extension(self, filename: str) -> str:
        """
        根据文件扩展名识别语言
        
        Args:
            filename: 文件名
        
        Returns:
            语言名称
        """
        ext = Path(filename).suffix.lower()
        for language, extensions in self.LANGUAGE_EXTENSIONS.items():
            if ext in extensions:
                return language
        return 'text'
    
    def _get_file_path(self, filename: str) -> Path:
        """获取文件的完整路径"""
        return self.base_dir / filename
    
    def _check_quota(self, additional_size: int = 0) -> Tuple[bool, str]:
        """
        检查会话配额
        
        Args:
            additional_size: 要添加的文件大小
        
        Returns:
            (是否在配额内, 错误消息)
        """
        total_size = sum(
            self._get_file_path(fname).stat().st_size 
            for fname in self.metadata['files'].keys()
            if self._get_file_path(fname).exists()
        )
        
        if total_size + additional_size > self.SESSION_QUOTA:
            used_mb = total_size / (1024 * 1024)
            quota_mb = self.SESSION_QUOTA / (1024 * 1024)
            return False, f"超出会话配额限制（已使用 {used_mb:.1f}MB / {quota_mb}MB）"
        
        return True, ""
    
    def create_file(self, filename: str, content: str = "") -> Dict:
        """
        创建新文件
        
        Args:
            filename: 文件名
            content: 文件内容
        
        Returns:
            操作结果
        """
        # 验证文件名
        valid, error = self._validate_filename(filename)
        if not valid:
            return {'success': False, 'error': error}
        
        file_path = self._get_file_path(filename)
        
        # 检查文件是否已存在
        if file_path.exists():
            return {'success': False, 'error': '文件已存在'}
        
        # 检查文件大小
        content_size = len(content.encode('utf-8'))
        if content_size > self.MAX_FILE_SIZE:
            return {'success': False, 'error': f'文件大小超过限制（{self.MAX_FILE_SIZE / (1024 * 1024)}MB）'}
        
        # 检查配额
        quota_ok, quota_error = self._check_quota(content_size)
        if not quota_ok:
            return {'success': False, 'error': quota_error}
        
        try:
            # 创建文件
            file_path.write_text(content, encoding='utf-8')
            
            # 更新元数据
            language = self._get_language_from_extension(filename)
            self.metadata['files'][filename] = {
                'language': language,
                'size': content_size,
                'created_at': datetime.now().isoformat(),
                'modified_at': datetime.now().isoformat()
            }
            self._save_metadata()
            
            return {
                'success': True,
                'filename': filename,
                'language': language,
                'size': content_size
            }
        except Exception as e:
            return {'success': False, 'error': f'创建文件失败: {str(e)}'}
    
    def read_file(self, filename: str) -> Dict:
        """
        读取文件内容
        
        Args:
            filename: 文件名
        
        Returns:
            操作结果
        """
        file_path = self._get_file_path(filename)
        
        if not file_path.exists():
            return {'success': False, 'error': '文件不存在'}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            metadata = self.metadata['files'].get(filename, {})
            
            return {
                'success': True,
                'filename': filename,
                'content': content,
                'language': metadata.get('language', 'text'),
                'size': len(content.encode('utf-8')),
                'modified_at': metadata.get('modified_at')
            }
        except Exception as e:
            return {'success': False, 'error': f'读取文件失败: {str(e)}'}
    
    def update_file(self, filename: str, content: str) -> Dict:
        """
        更新文件内容
        
        Args:
            filename: 文件名
            content: 新内容
        
        Returns:
            操作结果
        """
        file_path = self._get_file_path(filename)
        
        if not file_path.exists():
            return {'success': False, 'error': '文件不存在'}
        
        # 检查文件大小
        content_size = len(content.encode('utf-8'))
        if content_size > self.MAX_FILE_SIZE:
            return {'success': False, 'error': f'文件大小超过限制（{self.MAX_FILE_SIZE / (1024 * 1024)}MB）'}
        
        # 检查配额（减去旧文件大小）
        old_size = file_path.stat().st_size if file_path.exists() else 0
        quota_ok, quota_error = self._check_quota(content_size - old_size)
        if not quota_ok:
            return {'success': False, 'error': quota_error}
        
        try:
            # 更新文件
            file_path.write_text(content, encoding='utf-8')
            
            # 更新元数据
            if filename in self.metadata['files']:
                self.metadata['files'][filename]['size'] = content_size
                self.metadata['files'][filename]['modified_at'] = datetime.now().isoformat()
            else:
                language = self._get_language_from_extension(filename)
                self.metadata['files'][filename] = {
                    'language': language,
                    'size': content_size,
                    'created_at': datetime.now().isoformat(),
                    'modified_at': datetime.now().isoformat()
                }
            self._save_metadata()
            
            return {
                'success': True,
                'filename': filename,
                'size': content_size
            }
        except Exception as e:
            return {'success': False, 'error': f'更新文件失败: {str(e)}'}
    
    def delete_file(self, filename: str) -> Dict:
        """
        删除文件
        
        Args:
            filename: 文件名
        
        Returns:
            操作结果
        """
        file_path = self._get_file_path(filename)
        
        if not file_path.exists():
            return {'success': False, 'error': '文件不存在'}
        
        try:
            # 删除文件
            file_path.unlink()
            
            # 更新元数据
            if filename in self.metadata['files']:
                del self.metadata['files'][filename]
                self._save_metadata()
            
            return {'success': True, 'filename': filename}
        except Exception as e:
            return {'success': False, 'error': f'删除文件失败: {str(e)}'}
    
    def rename_file(self, old_filename: str, new_filename: str) -> Dict:
        """
        重命名文件
        
        Args:
            old_filename: 旧文件名
            new_filename: 新文件名
        
        Returns:
            操作结果
        """
        # 验证新文件名
        valid, error = self._validate_filename(new_filename)
        if not valid:
            return {'success': False, 'error': error}
        
        old_path = self._get_file_path(old_filename)
        new_path = self._get_file_path(new_filename)
        
        if not old_path.exists():
            return {'success': False, 'error': '文件不存在'}
        
        if new_path.exists():
            return {'success': False, 'error': '目标文件名已存在'}
        
        try:
            # 重命名文件
            old_path.rename(new_path)
            
            # 更新元数据
            if old_filename in self.metadata['files']:
                metadata = self.metadata['files'][old_filename]
                del self.metadata['files'][old_filename]
                
                # 更新语言识别
                metadata['language'] = self._get_language_from_extension(new_filename)
                metadata['modified_at'] = datetime.now().isoformat()
                
                self.metadata['files'][new_filename] = metadata
                self._save_metadata()
            
            return {
                'success': True,
                'old_filename': old_filename,
                'new_filename': new_filename
            }
        except Exception as e:
            return {'success': False, 'error': f'重命名文件失败: {str(e)}'}
    
    def list_files(self) -> Dict:
        """
        列出所有文件
        
        Returns:
            文件列表
        """
        try:
            files = []
            for filename, metadata in self.metadata['files'].items():
                file_path = self._get_file_path(filename)
                if file_path.exists():
                    files.append({
                        'filename': filename,
                        'language': metadata.get('language', 'text'),
                        'size': metadata.get('size', 0),
                        'created_at': metadata.get('created_at'),
                        'modified_at': metadata.get('modified_at')
                    })
            
            return {
                'success': True,
                'files': files,
                'total': len(files)
            }
        except Exception as e:
            return {'success': False, 'error': f'列出文件失败: {str(e)}'}
    
    def create_folder(self, folder_name: str) -> Dict:
        """
        创建文件夹
        
        Args:
            folder_name: 文件夹名
        
        Returns:
            操作结果
        """
        # 验证文件夹名
        valid, error = self._validate_filename(folder_name)
        if not valid:
            return {'success': False, 'error': error}
        
        folder_path = self.base_dir / folder_name
        
        if folder_path.exists():
            return {'success': False, 'error': '文件夹已存在'}
        
        try:
            folder_path.mkdir(parents=True)
            
            # 更新元数据
            if folder_name not in self.metadata['folders']:
                self.metadata['folders'].append(folder_name)
                self._save_metadata()
            
            return {'success': True, 'folder_name': folder_name}
        except Exception as e:
            return {'success': False, 'error': f'创建文件夹失败: {str(e)}'}
    
    def get_quota_info(self) -> Dict:
        """
        获取配额信息
        
        Returns:
            配额信息
        """
        try:
            total_size = sum(
                self._get_file_path(fname).stat().st_size 
                for fname in self.metadata['files'].keys()
                if self._get_file_path(fname).exists()
            )
            
            return {
                'success': True,
                'used': total_size,
                'quota': self.SESSION_QUOTA,
                'used_mb': round(total_size / (1024 * 1024), 2),
                'quota_mb': round(self.SESSION_QUOTA / (1024 * 1024), 2),
                'percentage': round((total_size / self.SESSION_QUOTA) * 100, 2)
            }
        except Exception as e:
            return {'success': False, 'error': f'获取配额信息失败: {str(e)}'}
