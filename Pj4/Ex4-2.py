import re
import argparse
import os
from datetime import datetime
from collections import defaultdict
import sys
import matplotlib.pyplot as plt
import numpy as np

# 日志行匹配的正则表达式
LOG_PATTERN = r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) - \[(.*?)\] "(GET|POST|PUT|DELETE|HEAD|OPTIONS) ([^ ?]+).*"'


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='日志分析工具', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--file', default='server.log', help='日志文件路径 (默认: server.log)')
    parser.add_argument('--start', help='开始时间 (格式: YYYY-MM-DD[ HH:MM:SS])')
    parser.add_argument('--end', help='结束时间 (格式: YYYY-MM-DD[ HH:MM:SS])')
    parser.add_argument('--append', action='store_true', help='追加模式 (默认覆盖)')
    parser.add_argument('--output', default='log_stats.txt', help='输出文件路径 (默认: log_stats.txt)')
    parser.add_argument('--plot', action='store_true', help='生成可视化柱状图')
    parser.add_argument('--plot-dir', default='plots', help='图表保存目录 (默认: plots)')
    return parser.parse_args()


def parse_datetime(time_str):
    """将字符串转换为datetime对象，支持不同时间精度"""
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d'
    ]
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"无效的时间格式: {time_str}")


def filter_time(log_time, start_dt, end_dt):
    """检查日志时间是否在指定范围内"""
    if start_dt and log_time < start_dt:
        return False
    if end_dt and log_time > end_dt:
        return False
    return True


def analyze_log(file_path, start_dt=None, end_dt=None):
    """分析日志文件并返回统计结果"""
    ip_counter = defaultdict(int)
    url_counter = defaultdict(int)
    invalid_count = 0
    total_lines = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                total_lines += 1
                match = re.match(LOG_PATTERN, line.strip())
                if not match:
                    invalid_count += 1
                    continue

                ip, time_str, _, url = match.groups()
                try:
                    log_dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    invalid_count += 1
                    continue

                if not filter_time(log_dt, start_dt, end_dt):
                    continue

                ip_counter[ip] += 1
                url_counter[url] += 1
    except FileNotFoundError:
        print(f"错误: 文件 {file_path} 不存在")
        sys.exit(1)
    except UnicodeDecodeError:
        try:
            # 尝试使用GBK编码再次打开
            print("尝试使用GBK编码重新读取文件...")
            with open(file_path, 'r', encoding='gbk') as f:
                for line in f:
                    total_lines += 1
                    match = re.match(LOG_PATTERN, line.strip())
                    if not match:
                        invalid_count += 1
                        continue

                    ip, time_str, _, url = match.groups()
                    try:
                        log_dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        invalid_count += 1
                        continue

                    if not filter_time(log_dt, start_dt, end_dt):
                        continue

                    ip_counter[ip] += 1
                    url_counter[url] += 1
        except:
            print(f"错误: 文件 {file_path} 编码问题，无法读取")
            sys.exit(1)

    return ip_counter, url_counter, invalid_count, total_lines


def save_results(ip_counter, url_counter, invalid_count, total_lines, args):
    """保存统计结果到文件，使用UTF-8编码避免中文乱码"""
    mode = 'a' if args.append else 'w'

    # 获取当前时间用于输出
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        with open(args.output, mode, encoding='utf-8') as f:
            # 添加分隔线和时间戳
            f.write(f"\n{'=' * 60}\n")
            f.write(f"日志分析报告 - 生成时间: {current_time}\n")
            f.write(f"{'=' * 60}\n\n")

            # 添加分析参数信息
            f.write(f"[分析参数]\n")
            f.write(f"日志文件: {args.file}\n")
            if args.start:
                f.write(f"开始时间: {args.start}\n")
            if args.end:
                f.write(f"结束时间: {args.end}\n")
            f.write(f"处理行数: {total_lines}\n")
            f.write(f"有效行数: {total_lines - invalid_count}\n")
            f.write(f"无效行数: {invalid_count}\n\n")

            # 处理IP统计
            f.write("=== 访问次数最多的IP ===\n")
            top_ips = sorted(ip_counter.items(), key=lambda x: x[1], reverse=True)[:10]
            for i, (ip, count) in enumerate(top_ips, 1):
                f.write(f"{i:2d}. IP: {ip:<15} 次数: {count}\n")

            # 处理URL统计
            f.write("\n=== 访问频率最高的URL ===\n")
            top_urls = sorted(url_counter.items(), key=lambda x: x[1], reverse=True)[:10]
            for i, (url, count) in enumerate(top_urls, 1):
                # 截断过长的URL
                display_url = url if len(url) <= 50 else url[:47] + "..."
                f.write(f"{i:2d}. URL: {display_url:<50} 次数: {count}\n")

            f.write("\n\n")

        print(f"分析完成! 结果已保存到 {args.output} (UTF-8编码)")
        print(f"处理行数: {total_lines}, 有效行数: {total_lines - invalid_count}, 无效行数: {invalid_count}")
    except IOError as e:
        print(f"文件写入错误: {e}")


def generate_bar_chart(data, title, xlabel, ylabel, filename, is_url=False):
    """生成柱状图并保存"""
    # 提取前10项
    items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    labels = [item[0] for item in items]
    counts = [item[1] for item in items]

    plt.figure(figsize=(12, 6))

    if is_url:
        # 对于URL使用横向柱状图，因为URL可能很长
        plt.barh(range(len(labels)), counts, color='#1f77b4')
        plt.yticks(range(len(labels)), labels)
        plt.xlabel(ylabel)
        plt.ylabel(xlabel)

        # 添加数值标签
        for i, v in enumerate(counts):
            plt.text(v + max(counts) * 0.01, i, str(v), color='black', va='center')
    else:
        # 对于IP使用纵向柱状图
        plt.bar(range(len(labels)), counts, color='#1f77b4')
        plt.xticks(range(len(labels)), labels, rotation=45, ha='right')
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        # 添加数值标签
        for i, v in enumerate(counts):
            plt.text(i, v + max(counts) * 0.01, str(v), ha='center')

    plt.title(title)
    plt.tight_layout()

    # 确保目录存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # 保存图表
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {filename}")


def main():
    args = parse_args()

    # 处理时间过滤参数
    start_dt = parse_datetime(args.start) if args.start else None
    end_dt = parse_datetime(args.end) if args.end else None

    # 分析日志
    ip_counter, url_counter, invalid_count, total_lines = analyze_log(
        args.file, start_dt, end_dt
    )

    # 保存文本结果
    save_results(ip_counter, url_counter, invalid_count, total_lines, args)

    # 生成可视化图表
    if args.plot:
        # 生成文件名前缀（基于输出文件名和时间）
        prefix = os.path.splitext(os.path.basename(args.output))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # IP访问统计图
        ip_chart_file = os.path.join(args.plot_dir, f"{prefix}_top_ips_{timestamp}.png")
        generate_bar_chart(
            ip_counter,
            "访问次数最多的IP",
            "IP地址",
            "访问次数",
            ip_chart_file
        )

        # URL访问统计图
        url_chart_file = os.path.join(args.plot_dir, f"{prefix}_top_urls_{timestamp}.png")
        generate_bar_chart(
            url_counter,
            "访问频率最高的URL",
            "URL路径",
            "访问次数",
            url_chart_file,
            is_url=True
        )

if __name__ == '__main__':
    main()