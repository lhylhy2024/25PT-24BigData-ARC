# -*- coding: utf-8 -*-
import re
import argparse
from collections import Counter
def load_stopwords(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        print(f"错误：未找到停用词文件 {file_path}")
        return set()
def clean_text(text):
    # 去除标点符号，只保留字母和汉字
    text = re.sub(r'[^\w\s]', '', text)
    return text.lower()
def process_text_file(text_file, stopwords, topn):
    try:
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        print(f"错误：无法读取文件 '{text_file}'，请确认编码为 UTF-8。")
        return
    cleaned_text = clean_text(text)
    words = cleaned_text.split()
    filtered_words = [word for word in words if word not in stopwords]
    word_counts = Counter(filtered_words)
    top_words = word_counts.most_common(topn)

    # 写入文件
    try:
        with open('word_freq.txt', 'w', encoding='utf-8') as f:
            for word, count in top_words:
                f.write(f"{word}\t{count}\n")
        print(f"已保存词频结果到 word_freq.txt")
    except Exception as e:
        print(f"写入文件时出错：{e}")

def main():
    parser = argparse.ArgumentParser(description="文本词频统计（不含可视化）")
    parser.add_argument('--text', type=str, default='sample.txt', help='输入的文本文件路径')
    parser.add_argument('--stopwords', type=str, default='stopwords.txt',help='停用词文件路径')
    parser.add_argument('--topn', type=int, default=10, help='输出前N个高频词')
    args = parser.parse_args()
    stopwords = load_stopwords(args.stopwords)
    process_text_file(args.text, stopwords, args.topn)
if __name__ == '__main__':
    main()
