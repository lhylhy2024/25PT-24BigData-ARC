import threading
from collections import Counter
import os
import time
import logging
import argparse
import jieba
import re

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载停用词
def load_stopwords(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return set(word.strip() for word in f if word.strip())
    except Exception as e:
        logging.error(f"读取停用词失败: {e}")
        return set()

# 线程任务：分词、过滤、统计
def count_words(text, stopwords, result_list, index):
    start_time = time.time()
    words = jieba.lcut(text)
    # 保留：纯中文、非停用词、长度为2~3个字的词
    filtered = [
        w for w in words
        if re.match(r'^[\u4e00-\u9fff]+$', w)
        and w not in stopwords
        and 2 <= len(w) <= 3
    ]
    word_count = Counter(filtered)
    result_list[index] = word_count
    elapsed = time.time() - start_time
    logging.info(f"线程-{index+1} 完成: 用时 {elapsed:.2f}s，词数: {len(filtered)}")

# 分片读取文件
def read_file_chunks(filepath, num_chunks):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_size = os.path.getsize(filepath)
        chunk_size = len(lines) // num_chunks
        chunks = [lines[i*chunk_size : (i+1)*chunk_size] for i in range(num_chunks - 1)]
        chunks.append(lines[(num_chunks - 1)*chunk_size:])  # 最后一块

        logging.info(f"文件大小: {total_size} 字节，{len(lines)} 行，分成 {num_chunks} 块")
        return [''.join(chunk) for chunk in chunks]

    except Exception as e:
        logging.error(f"读取文件失败: {e}")
        return []

# 主逻辑
def main(file_path='large_text.txt', stopwords_path='stopwords.txt', num_threads=4, output_path='word_counts.txt'):
    stopwords = load_stopwords(stopwords_path)
    if not stopwords:
        logging.warning("停用词列表为空，将不会过滤任何词。")

    chunks = read_file_chunks(file_path, num_threads)
    if not chunks:
        return

    threads = []
    results = [None] * num_threads

    for i in range(num_threads):
        t = threading.Thread(target=count_words, args=(chunks[i], stopwords, results, i))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # 合并Counter
    final_count = Counter()
    for c in results:
        final_count.update(c)

    # 输出前10高频词
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for word, count in final_count.most_common(10):
                f.write(f"{word}: {count}\n")
        logging.info(f"高频词已写入 {output_path}")
    except Exception as e:
        logging.error(f"写入文件失败: {e}")

# 命令行接口
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="中文多线程词频统计器")
    parser.add_argument('--file', type=str, default='large_text.txt', help='输入文本路径')
    parser.add_argument('--stopwords', type=str, default='stopwords.txt', help='停用词路径')
    parser.add_argument('--threads', type=int, default=4, help='线程数量')
    parser.add_argument('--output', type=str, default='word_counts.txt', help='输出路径')
    args = parser.parse_args()

    main(args.file, args.stopwords, args.threads, args.output)
