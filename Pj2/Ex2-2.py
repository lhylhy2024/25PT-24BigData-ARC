import re
import argparse
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib
import os
import sys
import jieba  # 添加中文分词库

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False


def read_file(file_path, encoding='utf-8'):
    """读取文件内容，处理编码错误"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"无法读取文件: {e}")
    except Exception as e:
        raise RuntimeError(f"读取文件失败: {e}")


def clean_text(text):
    """清洗文本：移除标点、转为小写"""
    # 移除非字母、非数字、非汉字的字符
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
    return text.lower()


def load_stopwords(stopwords_file):
    """加载停用词表，处理文件缺失"""
    default_stopwords = {
        '的', '是', '在', '和', '了', '与', '或', '为', '于', '由', '从', '到', '被', '将',
        '而', '及', '但', '如果', '因为', '所以', '虽然', '但是', '通过', '可以', '需要', '一个',
        '每个', '所有', '这个', '那个', '这些', '那些', '什么', '如何', '这样', '那样', '我们',
        '你们', '他们', '它们', '就是', '已经', '正在', '可能', '应该', '能够', '必须', '还是',
        '非常', '比较', '有', '也', '都', '不', '没', '没有', '我', '你', '他', '她', '它', '这',
        '那', '哪', '谁', '怎么', '为什么', '然后', '那么', '可是', '然而', '因此', '而且', '或者'
    }

    if not os.path.exists(stopwords_file):
        print(f"警告：停用词文件 '{stopwords_file}' 不存在，使用默认停用词表")
        return default_stopwords

    try:
        with open(stopwords_file, 'r', encoding='utf-8') as f:
            stopwords = set(line.strip().lower() for line in f if line.strip())
            return stopwords | default_stopwords  # 合并自定义和默认停用词
    except Exception as e:
        print(f"加载停用词出错: {e}，使用默认停用词")
        return default_stopwords


def segment_text(text, use_jieba=True):
    """中文分词处理"""
    if use_jieba:
        try:
            # 使用jieba分词并过滤单字
            return [word for word in jieba.cut(text) if len(word) >= 2]
        except:
            print("警告：jieba分词失败，使用基础分词")

    # 基础分词作为后备
    return re.findall(r'[\w\u4e00-\u9fff]{2,}', text)


def main():
    # 参数配置
    parser = argparse.ArgumentParser(description='文本高频词分析')
    parser.add_argument('--input', default='sample.txt', help='输入文件路径')
    parser.add_argument('--stopwords', default='stopwords.txt', help='停用词文件路径')
    parser.add_argument('--output', default='word_freq.txt', help='词频输出文件')
    parser.add_argument('--top', type=int, default=15, help='显示前N个高频词')
    parser.add_argument('--min-len', type=int, default=2, help='单词最小长度')
    parser.add_argument('--min-freq', type=int, default=3, help='最小出现次数')
    args = parser.parse_args()

    try:
        # 1. 读取文件
        text = read_file(args.input)
        print(f"成功读取文件: {args.input} ({len(text)} 字符)")

        # 2. 清洗文本
        cleaned_text = clean_text(text)

        # 3. 加载停用词
        stopwords = load_stopwords(args.stopwords)
        print(f"使用停用词: {len(stopwords)} 个")

        # 4. 分词并过滤
        words = segment_text(cleaned_text)
        print(f"初始分词数量: {len(words)}")

        # 过滤停用词和短词
        filtered_words = [
            word for word in words
            if (word not in stopwords)
               and (len(word) >= args.min_len)
        ]

        print(f"过滤后有效词汇: {len(filtered_words)}")

        # 5. 统计词频
        word_counts = Counter(filtered_words)

        # 过滤低频词
        filtered_counts = {word: count for word, count in word_counts.items() if count >= args.min_freq}
        print(f"满足最小频次({args.min_freq})的词汇: {len(filtered_counts)}")

        # 获取前N高频词
        top_words = sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True)[:args.top]

        if not top_words:
            print("没有满足条件的高频词")
            return

        # 6. 输出结果
        print(f"\n前 {args.top} 个高频词 (最小长度={args.min_len}, 最小频次={args.min_freq}):")
        for i, (word, count) in enumerate(top_words, 1):
            print(f"{i}. {word}: {count}")

        # 7. 保存词频结果
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(f"高频词统计结果 (共 {len(filtered_counts)} 个有效词)\n")
            f.write("===============================\n")
            f.write(f"词语\t出现次数\n")
            for word, count in sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{word}\t{count}\n")
        print(f"\n高频词结果已保存到: {args.output}")

        # 8. 绘制柱状图
        words, counts = zip(*top_words)
        plt.figure(figsize=(12, 7))
        bars = plt.bar(words, counts, color='#4c72b0')

        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{height}', ha='center', va='bottom', fontsize=9)

        plt.title(f'文本高频词 TOP-{args.top}', fontsize=14)
        plt.xlabel('关键词', fontsize=12)
        plt.ylabel('出现频次', fontsize=12)
        plt.xticks(rotation=45, ha='right', fontsize=10)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        # 保存图表
        plt.savefig('keywords_analysis.png', dpi=300, bbox_inches='tight')
        print("高频词分析图已保存为: keywords_analysis.png")
        plt.show()

    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 初始化jieba分词器
    jieba.initialize()
    main()