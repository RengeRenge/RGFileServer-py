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

# if __name__ == '__main__':
#     gi = GifInfo("/home/glcsnz123/images/psb.gif")
#     gi.crop_gif_bywh((23, 23), (220, 220))
#     gi.rotate_gif(90)
#     gi.fix_scale(95, 95)
#     gf = Gifsicle()
#     gf.convert(gi, "/home/glcsnz123/images/test.gif")
#     print
#     str(gi)
