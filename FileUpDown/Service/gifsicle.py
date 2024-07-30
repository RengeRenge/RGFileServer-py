#! /usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import os
import logging as L

logging = L.getLogger("file")


def compress(input, output, optimize=3, colors=64, lossy=20, width=200, height=200):
    """
    --optimize 或 -O: 启用 GIF 优化。可以接受的值为 1 到 3 表示优化的程度。数值越高，优化越激进，文件大小越小，但处理时间可能会增加。
        -O1: 基本优化，去除无效数据和重复帧。
        -O2: 更激进的优化，合并重复的帧，减少颜色表的大小。
        -O3: 最激进的优化，尝试重新压缩图像数据。
    --colors 或 -k: 设置 GIF 中使用的最大颜色数。这可以减少文件大小，但可能会影响图像质量。
        -k 64: 将颜色数限制为 64。
    --lossy: 启用有损压缩，可以大幅度减小文件大小，但可能会影响图像质量。
    --crop: 裁剪 GIF 图像，只保留感兴趣的部分。
    --resize 或 --resize-width, --resize-height: 调整 GIF 的尺寸，改变宽度或高度。
    --unoptimize: 取消优化，将 GIF 返回到未优化的状态。
    """
    command = [
        "gifsicle",
        "--batch",
        f"--lossy={lossy}",
        f"--optimize={optimize}",
        "--colors",
        str(colors),
        "--resize-fit",
        f"{width}x{height}",
        input,
        "-o",
        output,
    ]

    re = False
    try:
        result = subprocess.run(
            command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        re = result.returncode == 0
        if re == False:
            if os.path.exists(output):
                os.remove(output)
        return re
    except subprocess.CalledProcessError as e:
        logging.error(e.stderr.decode(), exc_info=True)
        if os.path.exists(output):
            os.remove(output)
    except Exception as e:
        logging.error(e, exc_info=True)
        if os.path.exists(output):
            os.remove(output)
    finally:
        return re


# if __name__ == '__main__':
#     if gifsicle.compress(path, cache_path, width=side, height=side, colors=color, lossy=lossy, optimize=optimize) == False:
#         logging.error('gifsicle compress failed')
#         abort(404)
