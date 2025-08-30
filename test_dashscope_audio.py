#!/usr/bin/env python3
"""
测试DashScope音频处理器
演示如何使用简化后的音频处理器进行语音识别
"""

import asyncio
import os
import json
from pathlib import Path
from src.utils.audio_processor import AudioProcessor

async def test_dashscope_audio_processor():
    """测试DashScope音频处理器"""
    
    # 示例视频文件路径（需要替换为实际存在的视频文件）
    video_path = Path("./subtitle_mode_test/video.mp4")
    output_path = Path("output_subtitles.srt")
    
    print("测试DashScope音频处理器...")
    print("注意：提取的音频文件将保存在 subtitle_mode_test 目录中")
    
    # 方法1：使用类实例
    processor = AudioProcessor()
    
    def progress_callback(message: str, progress: float):
        print(f"[{progress:.1f}%] {message}")
    
    try:
        if video_path.exists():
            print(f"处理视频文件: {video_path}")
            
            result_path = await processor.generate_subtitles_from_video(
                video_path=video_path,
                output_path=output_path,
                progress_callback=progress_callback
            )
            
            print(f"字幕生成完成: {result_path}")
        else:
            print(f"视频文件不存在: {video_path}")
            print("请将示例视频文件放置在正确位置后重新运行测试")
    
    except Exception as e:
        print(f"处理失败: {e}")
    
    finally:
        # 清理临时文件
        processor.cleanup_temp_files()

async def test_direct_audio_subtitle():
    """
    直接测试音频字幕提取功能
    调用 audio_processor.py 中的 generate_subtitles_dashscope 方法
    """
    print("\n=== 直接测试音频字幕提取 ===")
    
    # 检查音频文件是否存在
    audio_path = Path("subtitle_mode_test/video.wav")
    
    if not audio_path.exists():
        print(f"❌ 音频文件不存在: {audio_path}")
        print("请先运行完整的视频处理流程生成音频文件，或手动放置音频文件")
        return None
    
    print(f"✅ 找到音频文件: {audio_path}")
    print(f"📊 音频文件大小: {audio_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # 创建音频处理器实例
    processor = AudioProcessor()
    
    # 进度回调函数
    def progress_callback(message: str, progress: float):
        print(f"[{progress:.1f}%] {message}")
    
    try:
        print("\n🚀 开始直接调用 DashScope 语音识别...")
        print("使用方法: AudioProcessor.generate_subtitles_dashscope()")
        
        # 直接调用 generate_subtitles_dashscope 方法
        subtitles = await processor.generate_subtitles_dashscope(
            audio_path=audio_path,
            progress_callback=progress_callback
        )
        
        if subtitles:
            print(f"\n🎉 字幕提取成功！共生成 {len(subtitles)} 条字幕")
            
            # 显示字幕内容
            print("\n📝 字幕内容预览:")
            print("=" * 60)
            for i, subtitle in enumerate(subtitles[:5]):  # 只显示前5条
                print(f"{subtitle['index']}")
                print(f"{subtitle['start_time']} --> {subtitle['end_time']}")
                print(f"{subtitle['text']}")
                print()
                
            if len(subtitles) > 5:
                print(f"... 还有 {len(subtitles) - 5} 条字幕")
            print("=" * 60)
            
            # 保存字幕文件
            output_path = Path("subtitle_mode_test/direct_test_subtitles.srt")
            processor.save_subtitles_to_srt(subtitles, output_path)
            print(f"💾 字幕已保存到: {output_path}")
            
            return subtitles
        else:
            print("❌ 未能提取到字幕内容")
            return None
            
    except Exception as e:
        print(f"❌ 字幕提取失败: {e}")
        import traceback
        print("详细错误信息:")
        traceback.print_exc()
        return None
    
    finally:
        # 清理临时文件
        processor.cleanup_temp_files()

async def test_dashscope_with_demo_audio():
    """
    使用DashScope官方示例音频进行测试
    """
    print("\n=== 使用官方示例音频测试 ===")
    
    try:
        from http import HTTPStatus
        from dashscope.audio.asr import Transcription
        import dashscope
        
        # 设置API密钥
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            api_key = "sk-1e840dee447d437c8bb36a675d7b3880"
            print("⚠️  使用测试API密钥，生产环境请设置DASHSCOPE_API_KEY环境变量")
        
        dashscope.api_key = api_key
        print(f"✅ DashScope API密钥已设置: {api_key[:8]}...{api_key[-4:]}")
        
        print("\n📤 使用官方示例音频进行测试...")
        print("音频文件: DashScope官方示例")
        print("使用模型: paraformer-v2")
        print("语言提示: zh, en")
        
        # 使用官方示例音频
        task_response = Transcription.async_call(
            model='paraformer-v2',
            file_urls=[
                'https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav',
                'https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_male2.wav'
            ],
            language_hints=['zh', 'en']
        )
        
        print(f"✅ 任务提交成功，状态码: {task_response.status_code}")
        if hasattr(task_response, 'output') and hasattr(task_response.output, 'task_id'):
            print(f"📋 任务ID: {task_response.output.task_id}")
        
        print("\n⏳ 等待识别结果...")
        transcribe_response = Transcription.wait(task=task_response.output.task_id)
        
        print(f"✅ 识别完成，状态码: {transcribe_response.status_code}")
        
        if transcribe_response.status_code == HTTPStatus.OK:
            print("\n🎉 官方示例音频识别成功！")
            print("=" * 60)
            print(json.dumps(transcribe_response.output, indent=4, ensure_ascii=False))
            print("=" * 60)
            print('✅ 官方示例测试完成!')
            return transcribe_response.output
        else:
            print(f"❌ 识别失败: {transcribe_response.status_code}")
            if hasattr(transcribe_response, 'message'):
                print(f"错误信息: {transcribe_response.message}")
            return None
            
    except ImportError:
        print("❌ 缺少DashScope SDK，请运行：pip install dashscope")
        return None
    except Exception as e:
        print(f"❌ 官方示例测试失败: {e}")
        return None

async def run_all_tests():
    """运行所有测试的主函数"""
    print("DashScope音频处理器测试")
    print("=" * 50)
    
    # 测试选项菜单
    print("\n请选择测试模式:")
    print("1. 完整音频处理流程测试（从视频提取音频并识别）")
    print("2. 直接测试音频字幕提取（调用 generate_subtitles_dashscope）")
    print("3. 使用官方示例音频测试DashScope API")
    print("4. 运行所有测试")
    print("0. 退出")
    
    try:
        choice = input("\n请输入选择 (0-4): ").strip()
        
        if choice == "0":
            print("👋 退出测试")
            return
            
        elif choice == "1":
            print("\n🚀 开始完整音频处理流程测试...")
            await test_dashscope_audio_processor()
            
        elif choice == "2":
            print("\n🚀 开始直接测试音频字幕提取...")
            result = await test_direct_audio_subtitle()
            if result:
                print("\n✅ 直接音频字幕提取测试成功!")
            else:
                print("\n❌ 直接音频字幕提取测试失败!")
                
        elif choice == "3":
            print("\n🚀 开始官方示例音频测试...")
            result = await test_dashscope_with_demo_audio()
            if result:
                print("\n✅ 官方示例测试成功!")
            else:
                print("\n❌ 官方示例测试失败!")
                
        elif choice == "4":
            print("\n🚀 开始运行所有测试...")
            
            # 测试1: 完整流程
            print("\n" + "="*60)
            print("测试1: 完整音频处理流程")
            print("="*60)
            await test_dashscope_audio_processor()
            
            # 测试2: 直接音频字幕提取
            print("\n" + "="*60)
            print("测试2: 直接音频字幕提取")
            print("="*60)
            await test_direct_audio_subtitle()
            
            # 测试3: 官方示例
            print("\n" + "="*60)
            print("测试3: 官方示例音频")
            print("="*60)
            await test_dashscope_with_demo_audio()
            
        else:
            print("❌ 无效选择，默认运行直接音频字幕提取测试")
            await test_direct_audio_subtitle()
            
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 运行测试菜单
    asyncio.run(run_all_tests())
    
    print("\n" + "="*60)
    print("📋 测试说明:")
    print("="*60)
    print("1. 完整流程测试: 从视频文件开始的完整处理（提取音频 + 字幕识别）")
    print("2. 直接音频测试: 直接调用 generate_subtitles_dashscope 方法")
    print("3. 官方示例测试: 使用DashScope提供的示例音频文件")
    print("4. 运行所有测试: 依次执行上述三个测试")
    print()
    print("📁 文件说明:")
    print("- 输入视频: subtitle_mode_test/video.mp4")
    print("- 提取音频: subtitle_mode_test/video.wav")
    print("- 输出字幕: subtitle_mode_test/direct_test_subtitles.srt")
    print()
    print("🔧 环境要求:")
    print("- 需要安装DashScope SDK: pip install dashscope")
    print("- 需要设置DASHSCOPE_API_KEY环境变量（或使用测试密钥）")
    print("- 需要FFmpeg用于音频提取")
    print("="*60)
    
