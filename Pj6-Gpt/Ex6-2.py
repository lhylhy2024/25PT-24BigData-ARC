import argparse
import logging
import sys
import re

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

# 设置中文字体和负号正常显示
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 黑体
matplotlib.rcParams['axes.unicode_minus'] = False


def setup_logging(log_file: str):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def parse_args():
    parser = argparse.ArgumentParser(description="时间序列分析：移动平均和异常检测。")
    parser.add_argument("--input", type=str, default="time_series.csv", help="输入 CSV 文件路径")
    parser.add_argument("--output", type=str, default="analyzed_series.csv", help="输出 CSV 文件路径")
    parser.add_argument("--window", type=int, default=7, help="移动平均窗口大小（天）")
    parser.add_argument("--threshold", type=float, default=2.0, help="异常检测阈值（标准差倍数）")
    parser.add_argument("--plot", type=str, default="series_plot.png", help="输出图像文件名")
    parser.add_argument("--log", type=str, default="analysis.log", help="日志文件路径")
    return parser.parse_args()


def read_and_validate(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, encoding='utf-8')
    except Exception as e:
        logging.error(f"读取 CSV 文件失败 {path}: {e}")
        sys.exit(1)

    df.columns = [col.strip() for col in df.columns]
    cols_map = {}
    for col in df.columns:
        low = col.lower()
        if re.search(r"^(日期|date)$", low):
            cols_map['date'] = col
        elif re.search(r"^(值|value)$", low):
            cols_map['value'] = col

    if 'date' not in cols_map or 'value' not in cols_map:
        logging.error(f"缺少必要列：找到 {df.columns.tolist()}，需要 '日期'/'date' 和 '值'/'value'.")
        sys.exit(1)

    def is_valid_date(s):
        return isinstance(s, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", s)

    valid_dates = df[cols_map['date']].astype(str).apply(is_valid_date)
    if not valid_dates.all():
        count_invalid = (~valid_dates).sum()
        logging.warning(f"发现 {count_invalid} 行日期格式无效，已删除这些行.")
        df = df[valid_dates]

    try:
        df['日期'] = pd.to_datetime(df[cols_map['date']], format="%Y-%m-%d")
    except Exception as e:
        logging.error(f"日期解析失败: {e}")
        sys.exit(1)

    df['值'] = pd.to_numeric(df[cols_map['value']], errors='coerce')
    if df['值'].isnull().any():
        count = df['值'].isnull().sum()
        logging.warning(f"发现 {count} 行数值无效，已删除这些行.")
        df = df.dropna(subset=['值'])

    df = df.sort_values(by='日期').reset_index(drop=True)
    return df[['日期', '值']]


def compute_moving_average(df: pd.DataFrame, window: int) -> pd.Series:
    return df['值'].rolling(window=window, min_periods=1).mean()


def detect_anomalies(values: pd.Series, multiplier: float) -> pd.Series:
    mean_val = values.mean()
    std_val = values.std()
    upper = mean_val + multiplier * std_val
    lower = mean_val - multiplier * std_val
    return (values > upper) | (values < lower)


def plot_series(df: pd.DataFrame, plot_file: str, window: int):
    plt.figure(figsize=(12, 6))
    plt.plot(df['日期'], df['值'], label='原始值')
    plt.plot(df['日期'], df['移动平均'], label=f"移动平均({window} 天)")
    anomalies = df[df['异常']]
    if not anomalies.empty:
        plt.scatter(anomalies['日期'], anomalies['值'], c='red', label='异常点')

    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    plt.xlabel('日期')
    plt.ylabel('值')
    plt.title('时间序列及其移动平均和异常检测')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(plot_file, dpi=300)
    plt.close()
    logging.info(f"图像已保存至 {plot_file}")


def main():
    args = parse_args()
    setup_logging(args.log)
    logging.info("开始时间序列分析")

    df = read_and_validate(args.input)
    logging.info(f"从 {args.input} 读取 {len(df)} 行数据")

    df['移动平均'] = compute_moving_average(df, args.window)
    logging.info(f"计算 {args.window} 天移动平均")

    df['异常'] = detect_anomalies(df['值'], args.threshold)
    num_anomalies = df['异常'].sum()
    logging.info(f"检测到 {num_anomalies} 个异常点（阈值 {args.threshold} 倍标准差）")

    df.to_csv(args.output, index=False, encoding='utf-8-sig')
    logging.info(f"分析结果已保存至 {args.output}")

    plot_series(df, args.plot, args.window)

    logging.info("分析完成")


if __name__ == '__main__':
    main()
