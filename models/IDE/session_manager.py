"""
会话管理系统
处理 IDE 会话的创建、保存和恢复
"""

import os
import json
import re
import uuid
import shutil
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta

# 会话 id 只允许字母数字、下划线和连字符，防止目录穿越
_SESSION_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


class IDESessionManager:
    """IDE 会话管理器"""

    def __init__(self, sessions_dir: str):
        """
        初始化会话管理器

        Args:
            sessions_dir: 会话存储目录
        """
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_dir(self, session_id: str) -> Path:
        """获取会话目录（校验 id 合法性，防止路径越界）"""
        if not session_id or not _SESSION_ID_RE.match(str(session_id)):
            raise ValueError(f"非法的 session_id: {session_id!r}")
        return self.sessions_dir / session_id
    
    def _get_session_file(self, session_id: str) -> Path:
        """获取会话状态文件"""
        return self._get_session_dir(session_id) / 'session.json'
    
    def create_session(self) -> Dict:
        """
        创建新会话
        
        Returns:
            会话信息
        """
        try:
            # 生成唯一的会话 ID
            session_id = f"ide_{uuid.uuid4().hex}"
            session_dir = self._get_session_dir(session_id)
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # 初始化会话状态
            session_state = {
                'session_id': session_id,
                'created_at': datetime.now().isoformat(),
                'last_accessed': datetime.now().isoformat(),
                'editor_state': {
                    'current_file': None,
                    'open_files': [],
                    'language': 'python',
                    'theme': 'vs-dark'
                },
                'files': []
            }
            
            # 保存会话状态
            session_file = self._get_session_file(session_id)
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_state, f, ensure_ascii=False, indent=2)
            
            return {
                'success': True,
                'session_id': session_id,
                'created_at': session_state['created_at']
            }
        except Exception as e:
            return {'success': False, 'error': f'创建会话失败: {str(e)}'}
    
    def load_session(self, session_id: str) -> Dict:
        """
        加载会话状态
        
        Args:
            session_id: 会话 ID
        
        Returns:
            会话状态
        """
        session_file = self._get_session_file(session_id)
        
        if not session_file.exists():
            return {'success': False, 'error': '会话不存在'}
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_state = json.load(f)
            
            # 更新最后访问时间
            session_state['last_accessed'] = datetime.now().isoformat()
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_state, f, ensure_ascii=False, indent=2)
            
            return {
                'success': True,
                'session_state': session_state
            }
        except Exception as e:
            return {'success': False, 'error': f'加载会话失败: {str(e)}'}
    
    def save_session(self, session_id: str, editor_state: Dict) -> Dict:
        """
        保存会话状态
        
        Args:
            session_id: 会话 ID
            editor_state: 编辑器状态
        
        Returns:
            操作结果
        """
        session_file = self._get_session_file(session_id)
        
        if not session_file.exists():
            return {'success': False, 'error': '会话不存在'}
        
        try:
            # 读取现有状态
            with open(session_file, 'r', encoding='utf-8') as f:
                session_state = json.load(f)
            
            # 更新编辑器状态
            session_state['editor_state'] = editor_state
            session_state['last_accessed'] = datetime.now().isoformat()
            
            # 保存状态
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_state, f, ensure_ascii=False, indent=2)
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': f'保存会话失败: {str(e)}'}
    
    def delete_session(self, session_id: str) -> Dict:
        """
        删除会话
        
        Args:
            session_id: 会话 ID
        
        Returns:
            操作结果
        """
        session_dir = self._get_session_dir(session_id)
        
        if not session_dir.exists():
            return {'success': False, 'error': '会话不存在'}
        
        try:
            shutil.rmtree(session_dir)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': f'删除会话失败: {str(e)}'}
    
    def list_sessions(self) -> Dict:
        """
        列出所有会话
        
        Returns:
            会话列表
        """
        try:
            sessions = []
            for session_dir in self.sessions_dir.iterdir():
                if session_dir.is_dir():
                    session_file = session_dir / 'session.json'
                    if session_file.exists():
                        try:
                            with open(session_file, 'r', encoding='utf-8') as f:
                                session_state = json.load(f)
                            sessions.append({
                                'session_id': session_state.get('session_id'),
                                'created_at': session_state.get('created_at'),
                                'last_accessed': session_state.get('last_accessed')
                            })
                        except Exception as e:
                            print(f"读取会话失败 {session_dir.name}: {e}")
            
            # 按最后访问时间排序
            sessions.sort(key=lambda x: x.get('last_accessed', ''), reverse=True)
            
            return {
                'success': True,
                'sessions': sessions,
                'total': len(sessions)
            }
        except Exception as e:
            return {'success': False, 'error': f'列出会话失败: {str(e)}'}
    
    def cleanup_old_sessions(self, days: int = 7) -> Dict:
        """
        清理超过指定天数的旧会话
        
        Args:
            days: 天数阈值
        
        Returns:
            清理结果
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            for session_dir in self.sessions_dir.iterdir():
                if session_dir.is_dir():
                    session_file = session_dir / 'session.json'
                    if session_file.exists():
                        try:
                            with open(session_file, 'r', encoding='utf-8') as f:
                                session_state = json.load(f)
                            
                            last_accessed = datetime.fromisoformat(
                                session_state.get('last_accessed', '')
                            )
                            
                            if last_accessed < cutoff_date:
                                shutil.rmtree(session_dir)
                                deleted_count += 1
                        except Exception as e:
                            print(f"清理会话失败 {session_dir.name}: {e}")
            
            return {
                'success': True,
                'deleted_count': deleted_count
            }
        except Exception as e:
            return {'success': False, 'error': f'清理会话失败: {str(e)}'}
    
    def get_session_info(self, session_id: str) -> Dict:
        """
        获取会话信息
        
        Args:
            session_id: 会话 ID
        
        Returns:
            会话信息
        """
        session_file = self._get_session_file(session_id)
        
        if not session_file.exists():
            return {'success': False, 'error': '会话不存在'}
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_state = json.load(f)
            
            # 计算会话目录大小
            session_dir = self._get_session_dir(session_id)
            total_size = sum(
                f.stat().st_size 
                for f in session_dir.rglob('*') 
                if f.is_file()
            )
            
            return {
                'success': True,
                'session_id': session_id,
                'created_at': session_state.get('created_at'),
                'last_accessed': session_state.get('last_accessed'),
                'size': total_size,
                'size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': len(session_state.get('files', []))
            }
        except Exception as e:
            return {'success': False, 'error': f'获取会话信息失败: {str(e)}'}
