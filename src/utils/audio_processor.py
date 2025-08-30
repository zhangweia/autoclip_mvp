import os
import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import subprocess
import json
import aiohttp

try:
    from .error_handler import ProcessingError, ValidationError
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from utils.error_handler import ProcessingError, ValidationError

logger = logging.getLogger(__name__)

class AudioProcessor:
    """音频处理和语音识别类 - 基于DashScope实现"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "autoclip_audio"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Create subtitle_mode_test directory for audio files
        self.audio_save_dir = Path("subtitle_mode_test")
        self.audio_save_dir.mkdir(exist_ok=True)
    
    def extract_audio_from_video(
        self, 
        video_path: Path, 
        output_path: Optional[Path] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Path:
        """
        从视频文件提取音频
        
        Args:
            video_path: 视频文件路径
            output_path: 音频输出路径，默认为临时文件
            progress_callback: 进度回调函数
            
        Returns:
            音频文件路径
        """
        if not video_path.exists():
            raise ValidationError(f"视频文件不存在: {video_path}")
        
        if output_path is None:
            output_path = self.audio_save_dir / f"{video_path.stem}.wav"
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if progress_callback:
                progress_callback("正在提取音频...", 10)
            
            # 使用FFmpeg提取音频
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-vn',  # 不处理视频
                '-acodec', 'pcm_s16le',  # 音频编码
                '-ar', '16000',  # 采样率16kHz（适合语音识别）
                '-ac', '1',  # 单声道
                '-y',  # 覆盖输出文件
                str(output_path)
            ]
            
            # 执行命令
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='ignore'
            )
            
            if result.returncode != 0:
                raise ProcessingError(f"音频提取失败: {result.stderr}")
            
            if progress_callback:
                progress_callback("音频提取完成", 30)
            
            logger.info(f"音频提取成功: {output_path}")
            return output_path
            
        except Exception as e:
            raise ProcessingError(f"音频提取异常: {str(e)}")
    
    async def generate_subtitles_dashscope(
        self, 
        audio_path: Path,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> List[Dict]:
        """
        使用阿里云DashScope语音识别生成字幕
        使用官方Python SDK实现
        
        Args:
            audio_path: 音频文件路径
            progress_callback: 进度回调函数
            
        Returns:
            字幕数据列表
        """
        try:
            from http import HTTPStatus
            from dashscope.audio.asr import Transcription
            import json
            
            if progress_callback:
                progress_callback("正在初始化DashScope语音识别...", 35)
            
            # 设置API密钥
            api_key = os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                # 如果环境变量没有，使用硬编码的密钥（仅用于测试）
                api_key = "sk-1e840dee447d437c8bb36a675d7b3880"
                logger.warning("使用测试API密钥，生产环境请设置DASHSCOPE_API_KEY环境变量")
            
            import dashscope
            dashscope.api_key = api_key
            logger.info(f"DashScope API密钥已设置: {api_key[:8]}...{api_key[-4:]}")
            
            if progress_callback:
                progress_callback("正在上传音频文件并开始识别...", 50)
            
            # 使用官方SDK进行异步语音识别，按照提供的样例代码格式
            logger.info(f"准备提交DashScope识别任务，音频文件: {audio_path}")
            logger.info(f"使用模型: paraformer-v2, 语言提示: zh, en")
            
            task_response = Transcription.async_call(
                model='paraformer-v2',
                file_urls=['http://118.145.91.190:18080/static/audio/video.wav'],  # 本地文件路径
                language_hints=['zh']  # "language_hints"只支持paraformer-v2模型
            )
            
            logger.info(f"DashScope任务提交响应状态: {task_response.status_code}")
            if hasattr(task_response, 'output') and hasattr(task_response.output, 'task_id'):
                logger.info(f"DashScope任务ID: {task_response.output.task_id}")
            
            if progress_callback:
                progress_callback("正在等待识别结果...", 60)
            
            # 等待异步任务完成
            logger.info("开始等待DashScope识别结果...")
            transcribe_response = Transcription.wait(task=task_response.output.task_id)
            logger.info(f"DashScope识别完成，响应状态: {transcribe_response.status_code}")
            
            if transcribe_response.status_code == HTTPStatus.OK:
                if progress_callback:
                    progress_callback("正在解析识别结果...", 80)
                
                # 解析识别结果，按照官方文档格式
                output = transcribe_response.output
                logger.info("DashScope识别成功，开始解析结果")
                logger.debug(f"原始识别结果: {json.dumps(output, indent=2, ensure_ascii=False)}")
                
                # 根据官方文档，需要从transcription_url获取实际的识别结果
                if hasattr(output, 'transcription_url') and output.transcription_url:
                    logger.info(f"从URL获取详细识别结果: {output.transcription_url}")
                    # 获取实际的识别结果
                    subtitles = await self._fetch_transcription_results(output.transcription_url)
                else:
                    # 如果没有transcription_url，尝试直接解析output
                    logger.info("直接解析识别结果")
                    subtitles = self._parse_dashscope_results(output)
                
                if progress_callback:
                    progress_callback("DashScope语音识别完成", 90)
                
                logger.info(f"DashScope语音识别完成，生成{len(subtitles)}条字幕")
                return subtitles
            else:
                error_msg = f"DashScope识别失败: {transcribe_response.status_code} - {transcribe_response.message}"
                logger.error(error_msg)
                raise ProcessingError(error_msg)
            
        except ImportError:
            raise ProcessingError("缺少DashScope SDK，请运行：pip install dashscope")
        except Exception as e:
            logger.error(f"DashScope语音识别失败: {e}")
            raise ProcessingError(f"DashScope语音识别失败: {str(e)}")

    async def _fetch_transcription_results(self, url: str) -> List[Dict]:
        """
        从DashScope返回的URL获取实际的识别结果
        
        Args:
            url: 包含识别结果的URL
            
        Returns:
            字幕数据列表
        """
        try:
            import aiohttp
            import json
            
            logger.info(f"正在从 {url} 获取识别结果...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.debug(f"获取到的原始内容长度: {len(content)} 字符")
                        
                        # 解析JSON内容
                        data = json.loads(content)
                        logger.info(f"成功获取识别结果，开始解析...")
                        logger.debug(f"JSON数据结构: file_url={data.get('file_url', 'N/A')}, transcripts数量={len(data.get('transcripts', []))}")
                        
                        return self._parse_dashscope_results(data)
                    else:
                        logger.error(f"获取识别结果失败，HTTP状态码: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"获取识别结果时发生错误: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return []

    def _parse_dashscope_results(self, output) -> List[Dict]:
        """
        解析DashScope返回的结果为字幕格式
        根据punctuation字段断句组成字幕时间段
        
        Args:
            output: DashScope返回的结果对象
            
        Returns:
            字幕数据列表
        """
        try:
            subtitles = []
            
            # 如果输出是json的字符串格式，先解析
            if isinstance(output, str):
                import json
                output = json.loads(output)
                logger.debug("解析字符串格式的输出为JSON对象")
            
            logger.debug(f"开始解析DashScope输出，类型: {type(output)}")
            
            # 根据用户提供的确切格式解析
            # 输出格式: {"file_url": "...", "properties": {...}, "transcripts": [...]}
            if isinstance(output, dict) and 'transcripts' in output:
                transcripts = output['transcripts']
                logger.info(f"找到 {len(transcripts)} 个transcript记录")
                
                # 只处理第一个transcript（通常只有一个）
                if transcripts and len(transcripts) > 0:
                    transcript = transcripts[0]
                    logger.debug(f"处理第1个transcript")
                    
                    # 查找sentences字段
                    if 'sentences' in transcript:
                        sentences = transcript['sentences']
                        logger.info(f"在transcript中找到 {len(sentences)} 个句子")
                        
                        # 遍历所有句子，使用智能断句算法
                        for sentence in sentences:
                            if 'words' in sentence:
                                words = sentence['words']
                                logger.debug(f"处理句子，包含 {len(words)} 个词")
                                
                                # 使用智能断句算法处理这个句子的词
                                sentence_subtitles = self._smart_segmentation(words, len(subtitles))
                                subtitles.extend(sentence_subtitles)
            
            logger.info(f"解析完成，共生成{len(subtitles)}条字幕")
            return subtitles
            
        except Exception as e:
            logger.warning(f"解析DashScope结果失败: {e}")
            import traceback
            logger.warning(f"解析错误详情: {traceback.format_exc()}")
            return []

    def _smart_segmentation(self, words: List[Dict], start_index: int = 0) -> List[Dict]:
        """
        简化的智能断句算法
        原则1: 优先在标点符号处断句
        原则2: 句子较长时按语义智能断句
        
        Args:
            words: 词列表，每个词包含text, punctuation, begin_time, end_time
            start_index: 起始字幕索引
            
        Returns:
            字幕数据列表
        """
        if not words:
            return []
        
        subtitles = []
        current_text = ""
        current_start_time = None
        current_end_time = None
        
        # 配置参数
        MAX_SUBTITLE_LENGTH = 25  # 最大字幕长度
        MIN_SUBTITLE_LENGTH = 3  # 最小字幕长度
        SEMANTIC_BREAK_LENGTH = 16  # 语义断句的长度阈值
        
        for i, word in enumerate(words):
            word_text = word.get('text', '')
            word_punctuation = word.get('punctuation', '')
            word_begin_time = word.get('begin_time', 0)
            word_end_time = word.get('end_time', 0)
            
            # 如果是第一个词，设置开始时间
            if current_start_time is None:
                current_start_time = word_begin_time
            
            # 添加词到当前文本
            current_text += word_text
            current_end_time = word_end_time
            
            # 添加标点符号
            if word_punctuation:
                current_text += word_punctuation
            
            # 决定是否断句
            should_break = False
            break_reason = ""
            
            # 原则1: 优先在标点符号处断句
            if word_punctuation:
                # 句子结束标点：强制断句
                if word_punctuation in ['。', '？', '！', '.', '?', '!']:
                    should_break = True
                    break_reason = "句子结束"
                
                # 逗号、分号：自然断句点
                elif word_punctuation in ['，', ',', '；', ';','、']:
                    should_break = True
                    break_reason = "逗号断句"
                
                # 顿号：适度断句（避免过短）
                # elif word_punctuation in ['、'] and len(current_text) >= MIN_SUBTITLE_LENGTH * 2:
                #     should_break = True
                #     break_reason = "顿号断句"
            
            # 原则2: 句子较长时按语义智能断句
            elif len(current_text) >= SEMANTIC_BREAK_LENGTH:
                # 检查是否可以在当前位置断句（避免在词中间断句）
                if len(current_text) >= MAX_SUBTITLE_LENGTH:
                    # 超过最大长度，必须断句
                    should_break = True
                    break_reason = "长度限制"
                elif self._is_good_semantic_break_point(words, i):
                    # 在语义合适的位置断句
                    should_break = True
                    break_reason = "语义断句"
            
            # 执行断句
            if should_break and current_text.strip():
                # 确保字幕长度合理
                if len(current_text.strip()) >= MIN_SUBTITLE_LENGTH:
                    subtitle = {
                        "index": start_index + len(subtitles) + 1,
                        "start_time": self._seconds_to_srt_time(current_start_time / 1000.0),
                        "end_time": self._seconds_to_srt_time(current_end_time / 1000.0),
                        "text": current_text.strip()
                    }
                    subtitles.append(subtitle)
                    logger.debug(f"添加字幕({break_reason}): [{subtitle['start_time']} -> {subtitle['end_time']}] {subtitle['text']}")
                    
                    # 重置当前字幕段
                    current_text = ""
                    current_start_time = None
                    current_end_time = None
        
        # 处理剩余的文本
        if current_text.strip():
            subtitle = {
                "index": start_index + len(subtitles) + 1,
                "start_time": self._seconds_to_srt_time(current_start_time / 1000.0),
                "end_time": self._seconds_to_srt_time(current_end_time / 1000.0),
                "text": current_text.strip()
            }
            subtitles.append(subtitle)
            logger.debug(f"添加剩余字幕: [{subtitle['start_time']} -> {subtitle['end_time']}] {subtitle['text']}")
        
        return subtitles

    def _is_good_semantic_break_point(self, words: List[Dict], current_index: int) -> bool:
        """
        判断当前位置是否是一个好的语义断句点
        
        Args:
            words: 词列表
            current_index: 当前词的索引
            
        Returns:
            是否是好的断句点
        """
        if current_index >= len(words) - 1:
            return True  # 最后一个词，可以断句
        
        current_word = words[current_index].get('text', '')
        next_word = words[current_index + 1].get('text', '') if current_index + 1 < len(words) else ''
        
        # 语义断句的启发式规则
        # 1. 在名词后断句（常见的中文名词结尾字）
        if current_word in ['方', '药', '丸', '人', '者', '症', '状', '用', '效', '果', '法', '理', '论', '学', '科', '医', '病', '治', '疗']:
            return True
        
        # 2. 在动词后断句（常见的中文动词）
        if current_word in ['是', '有', '用', '治', '补', '服', '说', '讲', '称', '为', '以', '可', '能', '会', '要', '去']:
            return True
        
        # 3. 在连接词前不断句
        if next_word in ['的', '了', '在', '与', '和', '或', '但', '而', '因', '所', '就', '都', '也', '还', '又', '再']:
            return False
        
        # 4. 在数词、量词后断句
        if current_word in ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '个', '种', '类', '次', '遍', '年', '月', '日']:
            return True
        
        # 默认情况：可以断句
        return True

    def _get_audio_duration(self, audio_path: Path) -> float:
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return float(info['format']['duration'])
            else:
                logger.warning(f"无法获取音频时长，使用默认值: {result.stderr}")
                return 60.0  # 默认60秒
                
        except Exception as e:
            logger.warning(f"获取音频时长异常: {e}")
            return 60.0
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """将秒数转换为SRT时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def save_subtitles_to_srt(self, subtitles: List[Dict], output_path: Path) -> None:
        """
        将字幕数据保存为SRT文件
        
        Args:
            subtitles: 字幕数据列表
            output_path: SRT文件输出路径
        """
        try:
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for subtitle in subtitles:
                    f.write(f"{subtitle['index']}\n")
                    f.write(f"{subtitle['start_time']} --> {subtitle['end_time']}\n")
                    f.write(f"{subtitle['text']}\n\n")
            
            logger.info(f"字幕已保存到: {output_path}")
            
        except Exception as e:
            raise ProcessingError(f"保存字幕文件失败: {str(e)}")
    
    async def generate_subtitles_from_video(
        self, 
        video_path: Path,
        output_path: Path,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Path:
        """
        从视频文件生成字幕的完整流程（仅使用DashScope）
        
        Args:
            video_path: 视频文件路径
            output_path: 字幕输出路径
            progress_callback: 进度回调函数
            
        Returns:
            生成的字幕文件路径
        """
        try:
            if progress_callback:
                progress_callback("开始处理视频文件...", 0)
            
            # 从音频生成字幕（仅使用DashScope）
            return await self._generate_subtitles_from_audio(video_path, output_path, progress_callback)
                
        except Exception as e:
            raise ProcessingError(f"视频字幕处理失败: {str(e)}")
    
    async def _generate_subtitles_from_audio(
        self,
        video_path: Path,
        output_path: Path,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Path:
        """
        从音频生成字幕的内部方法（仅使用DashScope）
        """
        try:
            # 1. 从视频提取音频
            audio_path = self.extract_audio_from_video(video_path, progress_callback=progress_callback)
            
            # 2. 使用DashScope进行语音识别
            subtitles = await self.generate_subtitles_dashscope(audio_path, progress_callback)
            
            # 3. 保存字幕文件
            if progress_callback:
                progress_callback("正在保存字幕文件...", 95)
            
            self.save_subtitles_to_srt(subtitles, output_path)
            
            # 4. Handle audio file preservation and cleanup
            try:
                # Only clean if the audio file is in temp directory, not in subtitle_mode_test
                if audio_path.exists() and audio_path.parent == self.temp_dir:
                    audio_path.unlink()
                    logger.info(f"Cleaned temporary audio file: {audio_path}")
                elif audio_path.exists() and audio_path.parent == self.audio_save_dir:
                    logger.info(f"Audio file preserved in subtitle_mode_test: {audio_path}")
            except Exception as e:
                logger.warning(f"Failed to handle audio file cleanup: {e}")
            
            if progress_callback:
                progress_callback("字幕生成完成", 100)
            
            logger.info(f"字幕生成流程完成: {output_path}")
            return output_path
            
        except Exception as e:
            # Clean up temporary files but preserve audio files in subtitle_mode_test
            try:
                audio_path_to_clean = locals().get('audio_path')
                if audio_path_to_clean and isinstance(audio_path_to_clean, Path) and audio_path_to_clean.exists():
                    # Only clean if it's in temp directory, not in subtitle_mode_test
                    if audio_path_to_clean.parent == self.temp_dir:
                        audio_path_to_clean.unlink()
                        logger.info(f"Cleaned temporary audio file during error handling: {audio_path_to_clean}")
                    else:
                        logger.info(f"Audio file preserved in subtitle_mode_test during error: {audio_path_to_clean}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean temporary files during error handling: {cleanup_error}")
            
            raise ProcessingError(f"从音频生成字幕失败: {str(e)}")
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.glob("*"):
                    file.unlink()
                logger.info("临时文件清理完成")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")