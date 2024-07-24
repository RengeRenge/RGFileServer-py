#! /usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import os


class GifInfo:  # gifsicle -I

    def __init__(self, imgfile):
        if not os.path.isfile(imgfile): return
        self.src = imgfile
        self.__rotate = ""
        self.__crops = ""
        self.__resizes = ""

    def resize_gif(self, width=None, height=None):
        if width is None and height is None: return False
        if width is None:
            self.__resizes = " --colors 256 --resize-height %d " % height
            return True
        if height is None:
            self.__resizes = " --colors 256 --resize-width %d " % width
            return True
        self.__resizes = " --colors 256 --resize %dx%d" % (width, height)
        return True

    def resize_fit_gif(self, width=None, height=None):
        if width is None and height is None: return False
        if width is None:
            self.__resizes = " --colors 256 --resize-fit-height %d " % (height)
            return True
        if height is None:
            self.__resizes = " --colors 256 --resize-fit-width %d " % (width)
            return True
        self.__resizes = " --colors 256 --resize-fit %dx%d " % (width, height)
        return True

    def fix_scale(self, Xscale, Yscale=None):
        self.__resizes = " --colors 256 --scale " + str(Xscale / 100.0)
        if Yscale is not None:
            self.__resizes += "x" + str(Yscale / 100.0)
        self.__resizes += " "

    def rotate_gif(self, degree=0):
        if degree == 90 or degree == "90":
            self.__rotate = " --rotate-90 "
        elif degree == 180 or degree == "180":
            self.__rotate = " --rotate-180 "
        elif degree == 270 or degree == "270":
            self.__rotate = " --rotate-270 "
        else:
            return False
        return True

    def crop_gif_bypos(self, lefttop, rightdown):
        if rightdown[0] < lefttop[0] or rightdown[1] < lefttop[1]: return False
        self.__crops = " --colors 256 --crop " + ','.join(map(str, lefttop)) + "-" + ",".join(map(str, rightdown)) + " "
        return True

    def crop_gif_bywh(self, lefttop, wh):
        if wh[0] <= 0 or wh[1] <= 0: return False
        self.__crops = " --colors 256 --crop " + ",".join(map(str, lefttop)) + "+" + "x".join(map(str, wh)) + " "
        return True

    def __str__(self):
        return " ".join([self.__crops, self.__rotate, self.__resizes, self.src])


class Gifsicle:
    def __init__(self):
        pass

    def convert(self, infile, outfile=None):
        if outfile is None:
            res = subprocess.check_call("gifsicle --batch " + str(infile))
            return res
        cmd = "gifsicle " + str(infile) + " > " + outfile
        res = subprocess.check_call(cmd, shell=True)
        return res
    
    
    def compress(self, input, output, optimize=3, colors=64, lossy=20, width=200, height=200):
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
            'gifsicle',
            '--batch',
            f"--lossy={lossy}",
            f'--optimize={optimize}',
            '--colors', str(colors),
            '--resize-fit', f'{width}x{height}',
            input,
            '-o', output
        ]
        
        re = False
        try:
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            re = result.returncode == 0
            if re == False:
                if os.path.exists(output):
                    os.remove(output)
            return re
        except subprocess.CalledProcessError as e:
            print("[Gifsicle] CalledProcessError:", e.stderr.decode())
            if os.path.exists(output):
                os.remove(output)
        except Exception as e:
            print(f"[Gifsicle] Exception: {str(e)}")
            if os.path.exists(output):
                os.remove(output)
        finally:
            return re


# if __name__ == '__main__':
#     gi = GifInfo("/home/glcsnz123/images/psb.gif")
#     gi.crop_gif_bywh((23, 23), (220, 220))
#     gi.rotate_gif(90)
#     gi.fix_scale(95, 95)
#     gf = Gifsicle()
#     gf.convert(gi, "/home/glcsnz123/images/test.gif")
#     print
#     str(gi)
