#!/usr/bin/env python
# encoding: utf-8
"""
This module handles file upload and download procedure.
"""
import os
import time

import exifread
import pngquant
from PIL import Image

import GlobalConfigContext
from Service.gifsicle import GifInfo, Gifsicle

pngquant.config(quant_file='./pngquant', max_quality=50, min_quality=30, ndeep=10, ndigits=1)


def perform_upload(data):
    """
    Perform upload a file to server at `{FileStore_Directory}/{filename}`.
    If there already exists a file with the same name,
    a random uuid string will be added at the front of
    the file preventing overwriting.
    :param data: file object
    :return: tuple of <success flag, actual filename/exception>
    """
    f = None
    ret_file_name = None
    try:
        from werkzeug.utils import secure_filename
        import uuid
        # ret_file_name = secure_filename(data.filename)  # Origin Flask secure function not support CHS
        ret_file_name = data.filename
        extension = os.path.splitext(ret_file_name)[-1]
        file_pre_name = os.path.splitext(ret_file_name)[0]
        uuidstr = ''

        upload_path = os.path.join(GlobalConfigContext.FileStore_Directory, ret_file_name)

        while os.path.exists(upload_path):
            uuidstr = "_" + str(uuid.uuid1()).split('-')[0]
            # ret_file_name = secure_filename(prefix + data.filename)  # Origin Flask secure function not support CHS
            ret_file_name = file_pre_name + uuidstr + extension
            upload_path = os.path.join(GlobalConfigContext.FileStore_Directory, ret_file_name)

        # stream write
        with open(upload_path, "wb") as f:
            buffer_size = 4096
            while f:
                stream_buffer = data.stream.read(buffer_size)
                if len(stream_buffer) == 0:

                    f.close()
                    f = None
                    exif = exif_date(upload_path)

                    if data.content_type.startswith('image/'):
                        im = Image.open(upload_path)

                        quality_name = file_pre_name + uuidstr + '_quality' + extension
                        quality_name_path = os.path.join(GlobalConfigContext.FileStore_Directory, quality_name)

                        if extension.endswith('gif'):
                            gi = GifInfo(upload_path)
                            gi.resize_fit_gif(width=256, height=256)
                            gf = Gifsicle()
                            if gf.convert(gi, outfile=quality_name_path) != 0:
                                raise Exception
                        elif extension.endswith('png'):
                            pngquant.quant_image(image=upload_path, dst=quality_name_path)
                        else:
                            im.save(quality_name_path, quality=50)

                        im.thumbnail(size=(600, 600))

                        thumb_name = file_pre_name + uuidstr + '_thumbnail' + extension
                        thumb_name_path = os.path.join(GlobalConfigContext.FileStore_Directory, thumb_name)
                        im.save(thumb_name_path)

                    return True, ret_file_name, "", exif
                f.write(stream_buffer)
            return False, ret_file_name, str('open failed'), 0,
    except Exception as ex:
        print(ex)
        return False, ret_file_name, str(ex), 0,
    finally:
        if f is not None:
            f.close()


def exif_date(filename):
    try:
        fd = open(filename, 'rb')
    except:
        raise "unopen file[%s]\\n" % filename

    data = exifread.process_file(fd)

    if data:
        try:
            t = data['EXIF DateTimeOriginal']

            # 转换为时间字符串
            t = str(t).replace("-", ":")

            # 转为时间数组
            time_array = time.strptime(t, '%Y:%m:%d %H:%M:%S')

            # 转化为时间戳
            timestamp = time.mktime(time_array) * 1000
            return timestamp
        except Exception as ex:
            pass
    return 0
    # # 如果没有取得 exif ，则用图像的创建日期，作为拍摄日期
    # state = os.stat(filename)
    # return time.strftime("%Y-%m-%d", time.localtime(state[-2]))


def perform_download(name):
    """
    Perform retrieve file location for downloading via its file name.
    :param name: file name string
    :return: tuple of <exist flag, file actual location>
    """
    find_path = os.path.join(GlobalConfigContext.FileStore_Directory, name)
    exist_flag = os.path.exists(find_path)
    return exist_flag, find_path
