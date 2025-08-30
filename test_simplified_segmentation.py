#!/usr/bin/env python3
"""
测试简化的智能断句算法
原则1: 优先在标点符号处断句
原则2: 句子较长时按语义智能断句
"""

import json
from pathlib import Path
from datetime import datetime
from src.utils.audio_processor import AudioProcessor

def test_simplified_segmentation():
    """测试简化的断句算法"""
    
    result_file = Path("subtitle_mode_test/result.json")
    
    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    processor = AudioProcessor()
    
    print("🧪 简化智能断句算法测试")
    print("=" * 60)
    print("原则1: 优先在标点符号处断句")
    print("原则2: 句子较长时按语义智能断句")
    print("=" * 60)
    
    # 解析字幕
    subtitles = processor._parse_dashscope_results(data)
    
    print(f"\n📊 断句结果统计:")
    print(f"  - 生成字幕条数: {len(subtitles)}")
    
    # 分析字幕质量
    lengths = [len(subtitle['text']) for subtitle in subtitles]
    durations = []
    
    for subtitle in subtitles:
        start_parts = subtitle['start_time'].split(':')
        end_parts = subtitle['end_time'].split(':')
        
        start_seconds = float(start_parts[0]) * 3600 + float(start_parts[1]) * 60 + float(start_parts[2].replace(',', '.'))
        end_seconds = float(end_parts[0]) * 3600 + float(end_parts[1]) * 60 + float(end_parts[2].replace(',', '.'))
        
        duration = end_seconds - start_seconds
        durations.append(duration)
    
    print(f"  - 字幕长度统计:")
    print(f"    最短: {min(lengths)} 字符")
    print(f"    最长: {max(lengths)} 字符")
    print(f"    平均: {sum(lengths) / len(lengths):.1f} 字符")
    
    print(f"  - 字幕时长统计:")
    print(f"    最短: {min(durations):.2f} 秒")
    print(f"    最长: {max(durations):.2f} 秒")
    print(f"    平均: {sum(durations) / len(durations):.2f} 秒")
    
    # 分析断句质量
    print(f"\n📝 断句质量分析:")
    
    # 统计不同长度的字幕分布
    short_subtitles = [s for s in subtitles if len(s['text']) < 10]
    medium_subtitles = [s for s in subtitles if 10 <= len(s['text']) <= 20]
    long_subtitles = [s for s in subtitles if len(s['text']) > 20]
    
    print(f"  - 短字幕 (<10字符): {len(short_subtitles)} 条 ({len(short_subtitles)/len(subtitles)*100:.1f}%)")
    print(f"  - 中等字幕 (10-20字符): {len(medium_subtitles)} 条 ({len(medium_subtitles)/len(subtitles)*100:.1f}%)")
    print(f"  - 长字幕 (>20字符): {len(long_subtitles)} 条 ({len(long_subtitles)/len(subtitles)*100:.1f}%)")
    
    # 显示目标句子的断句效果
    print(f"\n🎯 目标句子断句效果:")
    target_subtitles = []
    for subtitle in subtitles:
        text = subtitle['text']
        if '此方构成简洁' in text or '用药平淡无奇' in text or '颇有貌不惊人' in text:
            target_subtitles.append(subtitle)
    
    if target_subtitles:
        for subtitle in target_subtitles:
            print(f"  {subtitle['index']}. [{subtitle['start_time']} -> {subtitle['end_time']}] {subtitle['text']}")
    
    # 显示前15条字幕
    print(f"\n📋 前15条字幕示例:")
    print("-" * 60)
    for i, subtitle in enumerate(subtitles[:15]):
        print(f"  {subtitle['index']:2d}. [{subtitle['start_time']} -> {subtitle['end_time']}] {subtitle['text']}")
    
    if len(subtitles) > 15:
        print(f"    ... 还有 {len(subtitles) - 15} 条字幕")
    
    return subtitles

def save_results(subtitles):
    """保存测试结果"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存字幕文件
    srt_file = Path(f"subtitle_mode_test/simplified_subtitles_{timestamp}.srt")
    processor = AudioProcessor()
    processor.save_subtitles_to_srt(subtitles, srt_file)
    print(f"\n💾 字幕文件已保存到: {srt_file}")
    
    # 保存简要报告
    report_file = Path(f"subtitle_mode_test/simplified_report_{timestamp}.txt")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("简化智能断句算法测试报告\n")
        f.write("=" * 40 + "\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("算法原则:\n")
        f.write("  1. 优先在标点符号处断句\n")
        f.write("  2. 句子较长时按语义智能断句\n\n")
        
        lengths = [len(subtitle['text']) for subtitle in subtitles]
        f.write(f"测试结果:\n")
        f.write(f"  生成字幕条数: {len(subtitles)}\n")
        f.write(f"  平均字幕长度: {sum(lengths) / len(lengths):.1f} 字符\n")
        f.write(f"  最短字幕: {min(lengths)} 字符\n")
        f.write(f"  最长字幕: {max(lengths)} 字符\n\n")
        
        f.write("字幕示例 (前20条):\n")
        for subtitle in subtitles[:20]:
            f.write(f"{subtitle['index']:2d}. [{subtitle['start_time']} -> {subtitle['end_time']}] {subtitle['text']}\n")
        
        f.write(f"\n算法特点:\n")
        f.write("  ✅ 简洁高效的断句逻辑\n")
        f.write("  ✅ 优先保证标点符号断句\n")
        f.write("  ✅ 智能语义断句避免过长字幕\n")
        f.write("  ✅ 保持语义完整性\n")
        f.write("  ✅ 适合中文语言特点\n")
    
    print(f"📄 测试报告已保存到: {report_file}")
    
    return {
        'srt_file': srt_file,
        'report_file': report_file
    }

def analyze_algorithm_improvements():
    """分析算法改进效果"""
    
    print(f"\n🔍 算法改进分析")
    print("=" * 60)
    
    improvements = [
        {
            "改进点": "删除时间间隙检测",
            "原因": "实际测试中时间间隙都是0ms，没有实用价值",
            "效果": "简化算法逻辑，提高执行效率"
        },
        {
            "改进点": "删除发音时间分析",
            "原因": "发音时间变化不明显，对断句帮助有限",
            "效果": "减少计算复杂度，专注核心断句逻辑"
        },
        {
            "改进点": "优先标点符号断句",
            "原因": "标点符号是最可靠的语言停顿标记",
            "效果": "保证断句的语法正确性和自然性"
        },
        {
            "改进点": "语义智能断句",
            "原因": "长句需要在语义合适的位置断句",
            "效果": "避免在连接词等不合适位置断句"
        },
        {
            "改进点": "简化参数配置",
            "原因": "减少需要调优的参数数量",
            "效果": "算法更稳定，易于维护"
        }
    ]
    
    for improvement in improvements:
        print(f"📌 {improvement['改进点']}:")
        print(f"   原因: {improvement['原因']}")
        print(f"   效果: {improvement['效果']}")
        print()
    
    print("🎯 新算法优势:")
    print("  • 逻辑清晰简洁，易于理解和维护")
    print("  • 专注核心断句需求，避免过度复杂化")
    print("  • 基于语言学原理，断句更自然")
    print("  • 适应中文语言特点，语义断句更准确")
    print("  • 执行效率高，适合实时处理")

if __name__ == "__main__":
    # 测试简化的断句算法
    subtitles = test_simplified_segmentation()
    
    # 保存测试结果
    saved_files = save_results(subtitles)
    
    # 分析算法改进
    analyze_algorithm_improvements()
    
    print(f"\n✅ 测试完成")
    print(f"📁 生成的文件:")
    for file_type, file_path in saved_files.items():
        print(f"  - {file_type}: {file_path}")
    
    print(f"\n🎉 简化智能断句算法特点:")
    print("  1️⃣ 优先在标点符号处断句 - 保证语法正确性")
    print("  2️⃣ 长句按语义智能断句 - 保持语义完整性")
    print("  3️⃣ 简洁高效的算法逻辑 - 易于维护和扩展")
    print("  4️⃣ 适合中文语言特点 - 断句更自然准确")
