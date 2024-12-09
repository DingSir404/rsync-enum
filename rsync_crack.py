import subprocess
import argparse
import logging
from pathlib import Path
from tqdm import tqdm
import time
import json
import csv

# 配置日志
logging.basicConfig(
    format='%(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_rsync(target_ip, path, port=873, timeout=None, verbose=False):
    """
    执行rsync命令以列出目录/文件。

    Args:
        target_ip (str): 目标IP地址。
        path (str): 要枚举的路径。
        port (int): rsync端口号。
        timeout (float): 命令执行超时时间（秒）。
        verbose (bool): 是否打印调试信息。
    """
    rsync_command = f'rsync -av --list-only rsync://{target_ip}:{port}/{path}'
    if verbose:
        logger.debug(f"执行命令: {rsync_command}")
    try:
        result = subprocess.run(
            rsync_command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        if result.stdout.strip():
            return result.stdout.strip()
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"运行rsync枚举命令失败: {e.stderr.strip()}")
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"运行rsync超时: {path}")
        return None

def download_rsync(target_ip, path, port=873, timeout=None, verbose=False):
    """
    使用rsync下载指定路径。
    """
    download_dir = Path("downloads")
    download_dir.mkdir(exist_ok=True)
    download_command = f'rsync -av rsync://{target_ip}:{port}/{path} {download_dir}/'
    if verbose:
        logger.debug(f"执行命令: {download_command}")
    try:
        subprocess.run(
            download_command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        logger.info(f"下载成功: {path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"下载失败 {path}: {e.stderr.strip()}")
    except subprocess.TimeoutExpired:
        logger.error(f"下载操作超时: {path}")

def save_results(found_paths, output_file, output_format):
    """
    将发现的路径保存到文件中，支持多种格式: plain/csv/json。

    Args:
        found_paths (list): 发现的路径列表。
        output_file (str): 输出文件名。
        output_format (str): 输出格式（plain/csv/json）。
    """
    if not output_file:
        return

    if output_format == 'plain':
        with open(output_file, 'w') as out_file:
            for path in found_paths:
                out_file.write(f"{path}\n")
    elif output_format == 'csv':
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Path"])
            for path in found_paths:
                writer.writerow([path])
    elif output_format == 'json':
        with open(output_file, 'w') as out_file:
            json.dump({"found_paths": found_paths}, out_file, indent=4)
    else:
        logger.error(f"不支持的输出格式: {output_format}")

    logger.info(f"\n已保存发现的路径到 {output_file}")

def main(target_ip, wordlist_file, extensions, output_file, download, port, exclude, down_rs_timeout, down_rs_delay, output_format, verbose):
    # 调整日志级别
    if verbose:
        logger.setLevel(logging.DEBUG)

    try:
        with open(wordlist_file, 'r') as file:
            words = file.read().splitlines()

        # 过滤掉需要排除的关键字
        if exclude:
            original_count = len(words)
            words = [w for w in words if all(ex not in w for ex in exclude)]
            filtered_count = len(words)
            logger.info(f"已过滤 {original_count - filtered_count} 条与排除列表匹配的条目.")

        total = len(words) * (len(extensions) if extensions else 1)
        found_paths = []

        logger.info("开始进行rsync枚举...")
        logger.info(f"目标IP: {target_ip}")
        logger.info(f"字典文件: {wordlist_file}")
        if extensions:
            logger.info(f"扩展名: {', '.join(extensions)}")
        logger.info(f"端口: {port}")
        logger.info(f"输出文件: {output_file if output_file else 'NULL'}")
        logger.info(f"下载功能: {'启用' if download else '禁用'}")
        logger.info(f"超时时间: {down_rs_timeout if down_rs_timeout else 'NULL'}秒")
        logger.info(f"延时: {down_rs_delay if down_rs_delay else 'NULL'}秒")
        logger.info(f"输出格式: {output_format}")
        logger.info("-" * 50)

        with tqdm(total=total, desc="枚举进度", unit="个", leave=False) as pbar:
            for word in words:
                if extensions:
                    for ext in extensions:
                        path = f"{word}{ext}"
                        output = run_rsync(target_ip, path, port, down_rs_timeout, verbose)
                        if output:
                            logger.info(f"  [+] 发现: {path}")
                            found_paths.append(path)
                            if download:
                                download_rsync(target_ip, path, port, down_rs_timeout, verbose)
                        pbar.update(1)
                        if down_rs_delay:
                            time.sleep(down_rs_delay)
                else:
                    path = word
                    output = run_rsync(target_ip, path, port, down_rs_timeout, verbose)
                    if output:
                        logger.info(f"  [+] 发现: {path}")
                        found_paths.append(path)
                        if download:
                            download_rsync(target_ip, path, port, down_rs_timeout, verbose)
                    pbar.update(1)
                    if down_rs_delay:
                        time.sleep(down_rs_delay)

        if found_paths and output_file:
            save_results(found_paths, output_file, output_format)

        logger.info("\n枚举完成。")

    except FileNotFoundError:
        logger.error(f"字典文件 '{wordlist_file}' 未找到。")
    except KeyboardInterrupt:
        logger.error("用户中断操作，谢谢使用。")
    except Exception as e:
        logger.error(f"发生未知错误: {e}")

if __name__ == "__main__":
    logger.info("")
    logger.info("***************************************************")
    logger.info("         rsync 服务枚举工具 (by DingTom) v2")
    logger.info("***************************************************")
    logger.info("")

    parser = argparse.ArgumentParser(description='Rsync 枚举工具（增强版）。')
    parser.add_argument('-t', '--target-ip', required=True, help='目标IP地址')
    parser.add_argument('-w', '--wordlist', required=True, help='字典文件路径')
    parser.add_argument('-e', '--extensions', nargs='*', help='要追加的文件扩展名（例如：.php .html）', default=[])
    parser.add_argument('-o', '--output', help='保存发现的目录/文件的路径')
    parser.add_argument('-d', '--download', action='store_true', help='下载发现的目录/文件')
    parser.add_argument('-p', '--port', type=int, default=873, help='rsync端口号（默认: 873）')
    parser.add_argument('--exclude', nargs='*', help='排除包含特定子字符串的路径', default=[])
    parser.add_argument('--timeout', type=float, help='子进程执行超时（秒）')
    parser.add_argument('--delay', type=float, help='每次请求后的延时（秒）', default=0)
    parser.add_argument('--format', choices=['plain', 'csv', 'json'], default='plain', help='输出格式（plain/csv/json）')
    parser.add_argument('--verbose', action='store_true', help='启用调试日志输出（DEBUG级别）')

    args = parser.parse_args()

    # 规范化扩展名（确保以点开头）
    normalized_extensions = [ext if ext.startswith('.') else f".{ext}" for ext in args.extensions]

    # 重命名参数
    down_rs_timeout = args.timeout
    down_rs_delay = args.delay

    main(
        target_ip=args.target_ip,
        wordlist_file=args.wordlist,
        extensions=normalized_extensions,
        output_file=args.output,
        download=args.download,
        port=args.port,
        exclude=args.exclude,
        down_rs_timeout=down_rs_timeout,
        down_rs_delay=down_rs_delay,
        output_format=args.format,
        verbose=args.verbose
    )
