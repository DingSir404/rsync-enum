import subprocess
import argparse
import logging
from pathlib import Path
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    format='%(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_rsync(target_ip, path, port=873):
    """
    执行rsync命令以列出目录/文件。

    Args:
        target_ip (str): 目标IP地址。
        path (str): 要枚举的路径。
        port (int): rsync端口号。

    Returns:
        str or None: 如果成功，返回rsync的输出；否则返回None。
    """
    rsync_command = f'rsync -av --list-only rsync://{target_ip}:{port}/{path}'
    try:
        result = subprocess.run(
            rsync_command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.stdout.strip():
            return result.stdout.strip()
        return None
    except subprocess.CalledProcessError:
        return None

def download_rsync(target_ip, path, port=873):
    """
    使用rsync下载指定路径。

    Args:
        target_ip (str): 目标IP地址。
        path (str): 要下载的路径。
        port (int): rsync端口号。
    """
    download_command = f'rsync -av rsync://{target_ip}:{port}/{path} ./{path}'
    try:
        subprocess.run(
            download_command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"下载成功: {path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"下载失败 {path}: {e.stderr.strip()}")

def main(target_ip, wordlist_file, extensions, output_file, download, port):
    try:
        with open(wordlist_file, 'r') as file:
            words = file.read().splitlines()

        total = len(words) * (len(extensions) if extensions else 1)
        found_paths = []

        logger.info("开始进行rsync枚举...")
        logger.info(f"目标IP: {target_ip}")
        logger.info(f"字典文件: {wordlist_file}")
        if extensions:
            logger.info(f"扩展名: {', '.join(extensions)}")
        logger.info(f"端口: {port}")
        logger.info(f"输出文件: {output_file if output_file else '无'}")
        logger.info(f"下载功能: {'启用' if download else '禁用'}")
        logger.info("-" * 50)

        with tqdm(total=total, desc="枚举进度", unit="个") as pbar:
            for word in words:
                if extensions:
                    for ext in extensions:
                        path = f"{word}{ext}"
                        output = run_rsync(target_ip, path, port)
                        if output:
                            logger.info(f"  [+] 发现: {path}")
                            found_paths.append(path)
                            if download:
                                download_rsync(target_ip, path, port)
                        pbar.update(1)
                else:
                    path = word
                    output = run_rsync(target_ip, path, port)
                    if output:
                        logger.info(f"  [+] 发现: {path}")
                        found_paths.append(path)
                        if download:
                            download_rsync(target_ip, path, port)
                    pbar.update(1)

        if found_paths and output_file:
            with open(output_file, 'w') as out_file:
                for path in found_paths:
                    out_file.write(f"{path}\n")
            logger.info(f"\n已保存发现的路径到 {output_file}")

        logger.info("\n枚举完成。")

    except FileNotFoundError:
        logger.error(f"字典文件 '{wordlist_file}' 未找到。")
    except KeyboardInterrupt:
        logger.error("谢谢使用。")
    except Exception as e:
        logger.error(f"发生错误: {e}")

if __name__ == "__main__":
    logger.info("")
    logger.info("***************************************************")
    logger.info("         rsync 服务枚举工具 (by DingTom)")
    logger.info("***************************************************")
    logger.info("")

    parser = argparse.ArgumentParser(description='Rsync 枚举工具。')
    parser.add_argument('-t', '--target-ip', required=True, help='目标IP地址')
    parser.add_argument('-w', '--wordlist', required=True, help='字典文件路径')
    parser.add_argument('-e', '--extensions', nargs='*', help='要追加的文件扩展名（例如：.php .html）', default=[])
    parser.add_argument('-o', '--output', help='保存发现的目录/文件的路径')
    parser.add_argument('-d', '--download', action='store_true', help='下载发现的目录/文件')
    parser.add_argument('-p', '--port', type=int, default=873, help='rsync端口号（默认: 873）')
    args = parser.parse_args()

    # 规范化扩展名（确保以点开头）
    normalized_extensions = [ext if ext.startswith('.') else f".{ext}" for ext in args.extensions]

    main(args.target_ip, args.wordlist, normalized_extensions, args.output, args.download, args.port)
