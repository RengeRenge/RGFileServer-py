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
from flask import json

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
                    exif = exif_data(upload_path)

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


def exif_data(filename):
    try:
        fd = open(filename, 'rb')

        exif = {}
        data = exifread.process_file(fd)
        if data:
            try:
                original = {}
                for att in data:
                    if hasattr(data[att], 'printable'):
                        original[att] = data[att].printable

                exif.update(original=original)

                # 拍摄时间
                if 'EXIF DateTimeOriginal' in data:
                    t = data['EXIF DateTimeOriginal']

                    # 转换为时间字符串
                    t = str(t).replace("-", ":")

                    # 转为时间数组
                    time_array = time.strptime(t, '%Y:%m:%d %H:%M:%S')

                    # 转化为时间戳
                    timestamp = time.mktime(time_array) * 1000

                    exif.update(timestamp=timestamp)
                # # 如果没有取得 exif ，则用图像的创建日期，作为拍摄日期
                # state = os.stat(filename)
                # return time.strftime("%Y-%m-%d", time.localtime(state[-2]))

                # 纬度 和 经度
                if 'GPS GPSLongitudeRef' in data and 'GPS GPSLongitudeRef' in data:
                    # 纬度
                    LatRef = data["GPS GPSLatitudeRef"].printable
                    Lat = data["GPS GPSLatitude"].printable[1:-1].replace(" ", "").replace("/", ",").split(",")
                    Lat = float(Lat[0]) + float(Lat[1]) / 60 + float(Lat[2]) / float(Lat[3]) / 3600
                    if LatRef != "N":
                        Lat = Lat * (-1)

                    # 经度
                    LonRef = data["GPS GPSLongitudeRef"].printable
                    Lon = data["GPS GPSLongitude"].printable[1:-1].replace(" ", "").replace("/", ",").split(",")
                    Lon = float(Lon[0]) + float(Lon[1]) / 60 + float(Lon[2]) / float(Lon[3]) / 3600
                    if LonRef != "E":
                        Lon = Lon * (-1)

                    exif.update(gps_lalo='%f,%f' % (Lat, Lon))
                return exif
            except Exception as ex:
                print(ex)
                return exif
            finally:
                fd.close()
        return exif
    except Exception as ex:
        raise "exif_data open file[%s] failed %s\n" % (filename, str(ex))


def perform_download(filename, is_import=False):
    """
    Perform retrieve file location for downloading via its file name.
    :param name: file name string
    :return: tuple of <exist flag, file actual location>
    """
    base_path = GlobalConfigContext.FileImport_Directory if is_import else GlobalConfigContext.FileStore_Directory
    find_path = os.path.join(base_path, filename)
    exist_flag = os.path.exists(find_path)
    return exist_flag, find_path
