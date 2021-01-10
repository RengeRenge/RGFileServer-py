#!/usr/bin/env python
# encoding: utf-8
"""
This module handles file upload and download procedure.
"""
import os
import time

import magic
import mimetypes
import GlobalConfigContext
import exifread
from exifread import IfdTag, Ratio
# import pngquant
from PIL import Image
from Service.gifsicle import GifInfo, Gifsicle
import hashlib

# quant_file = GlobalConfigContext.Base_Directory + '/pngquant'
# pngquant.config(quant_file=quant_file, max_quality=80, min_quality=65)


image_support = [
    'bmp',
    'dib',
    'gif',
    'tiff',
    'tif',
    'jpeg',
    'jpg',
    'jpe',
    'ppm',
    'png',
    'bufr',
    'pcx',
    'eps',
    'fits',
    'grib',
    'hdf5',
    'jpeg2000',
    'ico',
    'im',
    'mpo',
    'msp',
    'palm',
    'pdf',
    'sgi',
    'spider',
    'tga',
    'webp',
    'wmf',
    'xbm'
]


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
    filename = None
    try:
        mime = magic.from_buffer(data.stream.read(2048), mime=True)
        data.stream.seek(0)

        # from werkzeug.utils import secure_filename
        import uuid
        # ret_file_name = secure_filename(data.filename)  # Origin Flask secure function not support CHS
        filename = data.filename

        name = os.path.splitext(filename)[0]
        extension = __extension(filename=filename, mime=mime, mime_guess=data.mimetype)
        random = ''
        upload_path = ''

        condition = True
        while condition:
            random = "_" + str(uuid.uuid1())
            # filename = secure_filename(prefix + data.filename)  # Origin Flask secure function not support CHS
            filename = name + random + extension
            upload_path = os.path.join(GlobalConfigContext.FileStore_Directory, filename)
            condition = os.path.exists(upload_path)

        # stream write
        with open(upload_path, "wb") as f:
            buffer_size = 4096
            while f:
                stream_buffer = data.stream.read(buffer_size)
                if len(stream_buffer) == 0:
                    f.close()

                    exif = __exif_data(upload_path)
                    file_size = os.path.getsize(upload_path)

                    if __support_image_compress(mime=mime, extension=extension):
                        __handle_image(path=upload_path, mime=mime, exif=exif, name=name + random, extension=extension)

                    return True, "", filename, mime, exif, file_size, __md5(upload_path)
                f.write(stream_buffer)
        raise Exception("open failed")
    except Exception as ex:
        print(ex)
        return False, str(ex), filename, None, 0, 0, ""
    finally:
        if f is not None:
            f.close()


def __rotate_image_if_need(image, exif):
    rotated = False
    try:
        if 'orientation' in exif:
            orientation = exif['orientation']
            if orientation == 3:
                rotated = True
                image = image.rotate(180, expand=True)
            elif orientation == 6:
                rotated = True
                image = image.rotate(270, expand=True)
            elif orientation == 8:
                rotated = True
                image = image.rotate(90, expand=True)
    except Exception as ex:
        print(ex)
        pass
    return image, rotated


def __extension(filename, mime, mime_guess):
    mime1 = mime.split(sep='/')[-1]
    mime_guess1 = mime_guess.split(sep='/')[-1]
    extension = None
    if mime1.find(mime_guess1) >= 0 or mime_guess1.find(mime1) >= 0:
        extension = __guess_extension(mime=mime, forward=mime1)
        if extension is None:
            extension = __guess_extension(mime=mime_guess, forward=mime_guess1)
    else:
        extension = __guess_extension(mime=mime, forward=mime1)
    if extension is None:
        extension = os.path.splitext(filename)[-1]
    if extension is None:
        extension = ""
    extension = extension.lower()
    return extension


def __guess_extension(mime, forward):
    extensions = mimetypes.guess_all_extensions(type=mime)
    length, guess_extension = 0, None
    for extension in extensions:
        if forward == extension:
            return extension
        this_length = len(extension)
        if this_length > length:
            length = this_length
            guess_extension = extension
    return guess_extension


def __support_image_compress(mime, extension):
    if mime.startswith('image/'):
        extension = extension.split(sep='.')[-1]
        if extension in image_support:
            return True
        return False


def __handle_image(path, mime, exif, name, extension):
    im = Image.open(path)
    rotated = False

    quality_name = name + '_quality' + extension
    quality_name_path = os.path.join(GlobalConfigContext.FileStore_Directory, quality_name)

    thumb_name = name + '_thumbnail' + extension
    thumb_name_path = os.path.join(GlobalConfigContext.FileStore_Directory, thumb_name)

    if mime.endswith('gif'):
        gi = GifInfo(path)
        gi.resize_fit_gif(width=256, height=256)
        gf = Gifsicle()
        if gf.convert(gi, outfile=quality_name_path) != 0:
            raise Exception
    else:
        im.thumbnail((1920, 1920), Image.ANTIALIAS)
        im, rotated = __rotate_image_if_need(image=im, exif=exif)
        im.save(quality_name_path, quality=80)

        # if extension.endswith('png'):
        #     im.save(quality_name_path)
        #     pngquant.quant_image(image=thumb_name_path, dst=quality_name_path)
        # else:
        #     im.save(quality_name_path)

    im.thumbnail((320, 320), Image.ANTIALIAS)
    if not rotated:
        im, rotated = __rotate_image_if_need(image=im, exif=exif)
    im.save(thumb_name_path)


def __exif_data(filename):
    try:
        fd = open(filename, 'rb')

        exif = {}
        data = exifread.process_file(fd)
        if data:
            try:
                original = {}
                for key in data:
                    ifd_tag = data[key]
                    if isinstance(ifd_tag, IfdTag):

                        if isinstance(ifd_tag.values, list):
                            values = []
                            for item in ifd_tag.values:
                                if isinstance(item, Ratio):
                                    values.append(item.__repr__())
                                else:
                                    values.append(item)
                        else:
                            values = ifd_tag.values

                        original[key] = {
                            'field_length': ifd_tag.field_length,
                            'field_offset': ifd_tag.field_offset,
                            'field_type': ifd_tag.field_type,
                            'tag': ifd_tag.tag,
                            'printable': ifd_tag.printable,
                            'values': values
                        }
                exif.update(original=original)

                if 'Image Orientation' in data:
                    t = data['Image Orientation']
                    exif.update(orientation=t.values[0] if len(t.values) > 0 else 0)

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
                    lat_ref = data["GPS GPSLatitudeRef"].printable
                    lat = data["GPS GPSLatitude"].printable[1:-1].replace(" ", "").replace("/", ",").split(",")
                    lat = float(lat[0]) + float(lat[1]) / 60 + float(lat[2]) / float(lat[3]) / 3600
                    if lat_ref != "N":
                        lat = lat * (-1)

                    # 经度
                    lon_ref = data["GPS GPSLongitudeRef"].printable
                    lon = data["GPS GPSLongitude"].printable[1:-1].replace(" ", "").replace("/", ",").split(",")
                    lon = float(lon[0]) + float(lon[1]) / 60 + float(lon[2]) / float(lon[3]) / 3600
                    if lon_ref != "E":
                        lon = lon * (-1)

                    exif.update(gps_lalo='%f,%f' % (lat, lon))
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


def perform_del(name):
    extension = os.path.splitext(name)[-1]
    file_pre_name = os.path.splitext(name)[0]

    path = os.path.join(GlobalConfigContext.FileStore_Directory, name)

    quality_name = file_pre_name + '_quality' + extension
    quality_name_path = os.path.join(GlobalConfigContext.FileStore_Directory, quality_name)

    thumb_name = file_pre_name + '_thumbnail' + extension
    thumb_name_path = os.path.join(GlobalConfigContext.FileStore_Directory, thumb_name)

    paths = [path, quality_name_path, thumb_name_path]

    result = True
    for path in paths:
        try:
            if os.path.exists(path):
                os.remove(path)
            else:
                pass
        except Exception as ex:
            print("perform_del")
            print(ex)
            result = False
    return result


def perform_info(name):
    path = os.path.join(GlobalConfigContext.FileStore_Directory, name)
    file_size = 0
    mime = None
    exif = None
    md5 = ""
    result = False
    msg = ""
    try:
        if os.path.exists(path):
            mime = magic.from_file(path, mime=True)
            file_size = os.path.getsize(path)
            exif = __exif_data(path)
            md5 = __md5(path)
            result = True
        else:
            pass
    except Exception as ex:
        print(ex)
        msg = str(ex)
    finally:
        return result, msg, name, mime, exif, file_size, md5


def __md5(filename):
    m = hashlib.md5()
    with open(filename, 'rb') as f:
        for line in f:
            m.update(line)
    md5code = m.hexdigest()
    # print(md5code)
    return md5code
