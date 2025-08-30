#!/usr/bin/env python3
"""
远程视频下载器 - 从用户服务器下载视频和字幕文件
"""

import os
import asyncio
import logging
import aiohttp
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from urllib.parse import urlparse

try:
    from .error_handler import FileIOError, ValidationError, ProcessingError
except ImportError:
    # 独立运行时的导入
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from utils.error_handler import FileIOError, ValidationError, ProcessingError

logger = logging.getLogger(__name__)

class RemoteDownloader:
    """远程视频下载器"""
    
    def __init__(self, download_dir: Optional[Path] = None):
        """
        初始化下载器
        
        Args:
            download_dir: 下载目录，默认为当前目录
        """
        self.download_dir = download_dir or Path.cwd()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def validate_url(self, url: str) -> bool:
        """
        验证URL格式
        
        Args:
            url: 文件URL
            
        Returns:
            是否为有效的URL
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def get_file_extension(self, url: str) -> str:
        """
        从URL获取文件扩展名
        
        Args:
            url: 文件URL
            
        Returns:
            文件扩展名
        """
        path = urlparse(url).path
        return Path(path).suffix.lower()
    
    async def download_file(
        self, 
        url: str, 
        output_path: Path,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        下载单个文件
        
        Args:
            url: 文件URL
            output_path: 输出路径
            progress_callback: 进度回调函数
            
        Returns:
            是否下载成功
        """
        if not self.validate_url(url):
            raise ValidationError(f"无效的URL: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                if progress_callback:
                    progress_callback(f"开始下载: {url}", 0)
                
                async with session.get(url) as response:
                    if response.status != 200:
                        raise ProcessingError(f"下载失败，HTTP状态码: {response.status}")
                    
                    # 获取文件总大小
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded_size = 0
                    
                    # 确保输出目录存在
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 下载文件
                    async with aiofiles.open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            # 更新进度
                            if progress_callback and total_size > 0:
                                progress = (downloaded_size / total_size) * 100
                                progress_callback(f"下载中: {output_path.name}", progress)
                
                if progress_callback:
                    progress_callback(f"下载完成: {output_path.name}", 100)
                
                logger.info(f"文件下载成功: {output_path}")
                return True
                
        except aiohttp.ClientError as e:
            raise ProcessingError(f"网络错误: {str(e)}")
        except Exception as e:
            raise ProcessingError(f"下载失败: {str(e)}")
    
    async def download_video_and_subtitle(
        self,
        video_url: str,
        subtitle_url: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, str]:
        """
        下载视频和字幕文件
        
        Args:
            video_url: 视频URL
            subtitle_url: 字幕URL（可选）
            progress_callback: 进度回调函数
            
        Returns:
            包含video_path和subtitle_path的字典
        """
        if not self.validate_url(video_url):
            raise ValidationError(f"无效的视频URL: {video_url}")
        
        # 生成文件名
        video_extension = self.get_file_extension(video_url) or '.mp4'
        video_filename = f"video{video_extension}"
        video_path = self.download_dir / video_filename
        
        subtitle_path = None
        if subtitle_url:
            if not self.validate_url(subtitle_url):
                raise ValidationError(f"无效的字幕URL: {subtitle_url}")
            
            subtitle_extension = self.get_file_extension(subtitle_url) or '.srt'
            subtitle_filename = f"subtitle{subtitle_extension}"
            subtitle_path = self.download_dir / subtitle_filename
        
        try:
            # 下载视频文件
            if progress_callback:
                progress_callback("开始下载视频文件...", 0)
            
            await self.download_file(
                video_url, 
                video_path, 
                lambda msg, prog: progress_callback(f"视频: {msg}", prog * 0.7) if progress_callback else None
            )
            
            # 下载字幕文件（如果提供）
            if subtitle_url and subtitle_path:
                if progress_callback:
                    progress_callback("开始下载字幕文件...", 70)
                
                await self.download_file(
                    subtitle_url,
                    subtitle_path,
                    lambda msg, prog: progress_callback(f"字幕: {msg}", 70 + prog * 0.3) if progress_callback else None
                )
            
            result = {
                'video_path': str(video_path),
                'subtitle_path': str(subtitle_path) if subtitle_path else ''
            }
            
            if progress_callback:
                progress_callback("下载完成", 100)
            
            logger.info(f"远程下载完成: 视频={video_path}, 字幕={subtitle_path}")
            return result
            
        except Exception as e:
            # 清理部分下载的文件
            for path in [video_path, subtitle_path]:
                if path and path.exists():
                    try:
                        path.unlink()
                    except:
                        pass
            raise e
    
    def cleanup_temp_files(self, *file_paths):
        """
        清理临时文件
        
        Args:
            *file_paths: 要清理的文件路径
        """
        for file_path in file_paths:
            if file_path and Path(file_path).exists():
                try:
                    Path(file_path).unlink()
                    logger.info(f"已清理临时文件: {file_path}")
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {file_path}, 错误: {e}")

# 便捷函数
async def download_remote_video(
    video_url: str,
    subtitle_url: Optional[str] = None,
    download_dir: Optional[Path] = None,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> Dict[str, str]:
    """
    下载远程视频和字幕的便捷函数
    
    Args:
        video_url: 视频URL
        subtitle_url: 字幕URL（可选）
        download_dir: 下载目录
        progress_callback: 进度回调函数
        
    Returns:
        包含video_path和subtitle_path的字典
    """
    downloader = RemoteDownloader(download_dir)
    return await downloader.download_video_and_subtitle(
        video_url, subtitle_url, progress_callback
    )

if __name__ == "__main__":
    # 测试代码
    async def test_download():
        # 测试下载
        result = await download_remote_video(
            "https://example.com/video.mp4",
            "https://example.com/subtitle.srt",
            Path("./test_downloads")
        )
        print(f"下载结果: {result}")
    
    # asyncio.run(test_download())