import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import logging
import argparse
import sys
import os
import codecs


# 配置中文字体支持
def configure_chinese_font():
    """配置中文字体支持，避免中文显示为方框"""
    try:
        # Windows系统使用SimHei
        if sys.platform.startswith('win'):
            plt.rcParams['font.sans-serif'] = ['SimHei']
        # macOS系统使用Heiti SC
        elif sys.platform.startswith('darwin'):
            plt.rcParams['font.sans-serif'] = ['Heiti SC']
        # Linux系统使用WenQuanYi Micro Hei
        else:
            plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']

        # 解决负号显示问题
        plt.rcParams['axes.unicode_minus'] = False
        return True
    except:
        return False


# 配置日志记录（解决乱码问题）
def configure_logging():
    """配置日志记录，解决中文乱码问题"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 文件处理器 - 使用UTF-8编码
    file_handler = logging.FileHandler('data_processing.log', mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)

    # 控制台处理器 - 输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def process_time_series(input_file, window_size=7, threshold=2):
    """处理时间序列数据的主函数"""
    logger = logging.getLogger()

    # 1. 读取并验证数据
    try:
        # 检查文件是否存在
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"文件不存在: {input_file}")

        # 检查文件编码
        try:
            with open(input_file, 'rb') as f:
                result = f.read(4096)
            encoding = 'utf-8' if result.startswith(codecs.BOM_UTF8) else None
        except:
            encoding = None

        logger.info(f"尝试读取文件: {input_file} (编码: {encoding or '自动检测'})")

        df = pd.read_csv(input_file, parse_dates=['date'], date_format='%Y-%m-%d', encoding=encoding)
        logger.info(f"成功读取文件，共 {len(df)} 条记录")

        # 验证数据完整性
        if df.isnull().any().any():
            nan_count = df.isnull().sum().sum()
            logger.warning(f"发现 {nan_count} 个空值，将进行清理")
            df = df.dropna()
            logger.info(f"清理后剩余 {len(df)} 条记录")

        # 验证日期格式
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            logger.error("日期格式解析失败，请确保日期列为YYYY-MM-DD格式")
            raise ValueError("日期格式解析失败")

    except Exception as e:
        logger.error(f"文件读取失败: {str(e)}", exc_info=True)
        raise

    # 2. 计算移动平均
    try:
        df.sort_values('date', inplace=True)  # 确保按日期排序
        logger.info(f"按日期排序数据，开始日期: {df['date'].min().date()}，结束日期: {df['date'].max().date()}")

        df['moving_avg'] = df['value'].rolling(window=window_size, min_periods=1).mean()
        logger.info(f"计算完成 {window_size} 天移动平均")
    except Exception as e:
        logger.error(f"移动平均计算失败: {str(e)}", exc_info=True)
        raise

    # 3. 检测异常点
    try:
        # 计算残差和标准差
        df['residual'] = df['value'] - df['moving_avg']
        std_dev = df['residual'].std()
        logger.info(f"残差标准差: {std_dev:.4f}")

        # 标记异常点
        df['is_anomaly'] = np.abs(df['residual']) > (threshold * std_dev)
        anomaly_count = df['is_anomaly'].sum()
        logger.info(f"检测到 {anomaly_count} 个异常点 (阈值 = {threshold}σ)")

        # 如果有异常点，记录详细信息
        if anomaly_count > 0:
            anomalies = df[df['is_anomaly']]
            for idx, row in anomalies.iterrows():
                logger.info(f"异常点: {row['date'].date()} - 值: {row['value']:.4f} (残差: {row['residual']:.4f})")
    except Exception as e:
        logger.error(f"异常检测失败: {str(e)}", exc_info=True)
        raise

    # 4. 绘制图表（添加中文支持）
    try:
        # 配置中文支持
        font_success = configure_chinese_font()

        plt.figure(figsize=(12, 6))

        # 绘制原始数据和移动平均线
        plt.plot(df['date'], df['value'], label='原始数据', color='blue', alpha=0.7)
        plt.plot(df['date'], df['moving_avg'], label=f'{window_size}天移动平均',
                 color='green', linewidth=2)

        # 标记异常点
        anomalies = df[df['is_anomaly']]
        plt.scatter(anomalies['date'], anomalies['value'],
                    color='red', s=50, label='异常点')

        # 使用中文标题和标签
        plt.title('时间序列分析', fontsize=14)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('数值', fontsize=12)

        # 添加网格和图例
        plt.grid(alpha=0.3)
        plt.legend()

        # 自动调整日期格式
        plt.gcf().autofmt_xdate()

        plt.tight_layout()
        plt.savefig('time_series_analysis.png')
        logger.info("图表已保存为 time_series_analysis.png")

        if not font_success:
            logger.warning("中文字体配置可能未成功，图表中的中文可能显示为方框")
    except Exception as e:
        logger.error(f"图表生成失败: {str(e)}", exc_info=True)
        raise

    # 5. 保存分析结果
    try:
        output_cols = ['date', 'value', 'moving_avg', 'is_anomaly']
        df[output_cols].to_csv('analyzed_series.csv', index=False, encoding='utf-8-sig')
        logger.info("分析结果已保存为 analyzed_series.csv (UTF-8 with BOM)")
    except Exception as e:
        logger.error(f"结果保存失败: {str(e)}", exc_info=True)
        raise

    return df


if __name__ == "__main__":
    # 配置日志记录
    logger = configure_logging()

    # 配置命令行参数
    parser = argparse.ArgumentParser(description='时间序列分析工具')
    parser.add_argument('--input', default='time_series.csv',
                        help='输入文件名 (默认: time_series.csv)')
    parser.add_argument('--window', type=int, default=7,
                        help='移动平均窗口大小 (默认: 7)')
    parser.add_argument('--threshold', type=float, default=2.0,
                        help='异常检测标准差阈值 (默认: 2.0)')

    args = parser.parse_args()

    print(f"""
    开始时间序列分析:
    输入文件: {args.input}
    移动平均窗口: {args.window} 天
    异常检测阈值: {args.threshold} 倍标准差
    """)

    try:
        result = process_time_series(
            input_file=args.input,
            window_size=args.window,
            threshold=args.threshold
        )
        print("\n分析成功完成! 生成文件:")
        print("- analyzed_series.csv: 分析结果数据")
        print("- time_series_analysis.png: 可视化图表")
        print("- data_processing.log: 处理日志")
    except Exception as e:
        print(f"\n处理失败: {str(e)}")
        print("请检查日志文件 data_processing.log 获取详细信息")