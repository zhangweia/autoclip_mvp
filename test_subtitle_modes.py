#!/usr/bin/env python3
"""
字幕模式功能测试 - 正确用法演示
展示如何使用 extract_mode 参数控制字幕处理方式
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.utils.remote_downloader import RemoteDownloader
from src.utils.audio_processor import generate_subtitles_from_video

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def progress_callback(message: str, progress: float):
    """进度回调函数"""
    print(f"[{progress:6.1f}%] {message}")

async def test_subtitle_extract_modes():
    """测试不同的字幕提取模式"""
    print("🎬 字幕模式功能测试")
    print("=" * 50)
    
    # 测试视频URL
    video_url = "http://118.145.91.190:18080/static/video/b46a0c016778ff0872b7702423138166.mp4"
    output_dir = Path("./subtitle_mode_test")
    output_dir.mkdir(exist_ok=True)
    
    print(f"📹 测试视频: {video_url}")
    print(f"📂 输出目录: {output_dir}")
    
    # 1. 下载视频文件
    print("\n📥 步骤1: 下载视频文件")
    downloader = RemoteDownloader(output_dir)
    # download_result = await downloader.download_video_and_subtitle(
    #     video_url=video_url,
    #     subtitle_url=None,  # 不传入字幕URL
    #     progress_callback=progress_callback
    # )
    
    # video_path = Path(download_result['video_path'])
    video_path  = Path("./subtitle_mode_test/video.mp4")
    print(f"✅ 视频下载完成: {video_path}")
    
    # 2. 测试不同的字幕模式
    print("\n🎤 步骤2: 测试不同字幕模式")
    
    # 定义测试模式
    test_modes = [
        {
            "mode": "generate",
            "description": "🎤 仅生成模式：使用Whisper语音识别生成字幕", 
            "output": "generate_whisper.srt",
            "method": "whisper"
        },
        {
            "mode": "generate",
            "description": "☁️ 仅生成模式：使用DashScope语音识别生成字幕", 
            "output": "generate_dashscope.srt",
            "method": "dashscope"
        }
    ]
    
    results = {}
    
    for config in test_modes:
        mode = config["mode"]
        description = config["description"] 
        output_file = config["output"]
        method = config.get("method", "dashscope")
        
        print(f"\n{description}")
        print("-" * 40)
        
        try:
            subtitle_path = output_dir / output_file
            
            # 🔑 关键：使用 extract_mode 参数控制字幕处理方式
            await generate_subtitles_from_video(
                video_path=video_path,           # 视频文件路径
                output_path=subtitle_path,       # 字幕输出路径
                progress_callback=progress_callback
            )
            
            if subtitle_path.exists():
                file_size = subtitle_path.stat().st_size
                print(f"✅ {mode} 模式成功: {file_size} bytes")
                
                # 显示字幕预览
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    content = f.read()[:200]
                    print(f"📄 预览: {content}...")
                
                results[f"{mode}_{method}"] = {"status": "success", "size": file_size}
            else:
                print(f"❌ {mode} 模式失败: 未生成文件")
                results[f"{mode}_{method}"] = {"status": "failed", "error": "未生成文件"}
                
        except Exception as e:
            print(f"❌ {mode} 模式异常: {e}")
            results[f"{mode}_{method}"] = {"status": "error", "error": str(e)}
    
    # 3. 结果汇总
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    for test_key, result in results.items():
        if "whisper" in test_key:
            display_name = f"🎤 Whisper 生成模式"
        elif "dashscope" in test_key:
            display_name = f"☁️ DashScope 生成模式"
        else:
            display_name = f"🤖 {test_key}"
        
        if result["status"] == "success":
            print(f"✅ {display_name}: 成功 ({result['size']} bytes)")
        else:
            print(f"❌ {display_name}: 失败 - {result.get('error', '未知错误')}")
    
    print(f"\n📁 生成的文件位置: {output_dir}")
    print("\n💡 关键要点:")
    print("   1. 使用 extract_mode 参数控制字幕处理方式")
    print("   2. 不要传入 subtitle_url，让系统根据 extract_mode 决定")
    print("   3. 'auto' 模式最智能，'extract'/'generate' 提供精确控制")

async def main():
    """主函数"""
    print("🎯 字幕模式正确用法演示")
    print("展示如何使用 extract_mode 参数而不是 subtitle_url")
    print()
    
    await test_subtitle_extract_modes()
    
    print("\n🎉 演示完成！")

if __name__ == "__main__":
    asyncio.run(main())