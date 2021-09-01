#!/usr/bin/env python
# encoding: utf-8
"""
This module handles file upload and download procedure.
"""
import os

import magic
import uuid
import GlobalConfigContext
# import pngquant
from PIL import Image

from Service import FileInfo
from Service.gifsicle import GifInfo, Gifsicle
import hashlib

RGThumbnailName = '_thumbnail'
RGQualityName = '_quality'
RGVideoThumbName = '_videoThumbnail.jpeg'
RGEpubThumbName = '_epubThumbnail.jpeg'

RGExtName = [RGThumbnailName, RGQualityName, RGVideoThumbName, RGEpubThumbName]

# quant_file = GlobalConfigContext.Base_Directory + '/pngquant'
# pngquant.config(quant_file=quant_file, max_quality=80, min_quality=65)


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
        mime = FileInfo.mime_type(buffer=data.stream, mime_guess=data.mimetype)
        filename = data.filename
        name = os.path.splitext(filename)[0]
        extension = FileInfo.extension(filename=filename, mime=mime, mime_guess=data.mimetype)
        random = ''
        upload_path = ''

        condition = True
        while condition:
            random = "_" + str(uuid.uuid1())
            # filename = secure_filename(prefix + data.filename)  # Origin Flask secure function not support CHS
            filename = name + random + extension
            upload_path = os.path.join(GlobalConfigContext.FileStore_Directory, filename)
            condition = os.path.exists(upload_path)
        name = name + random

        # stream write
        if not __write_to_path(path=upload_path, stream=data.stream):
            raise Exception("write failed")

        exif = FileInfo.exif_data(upload_path)
        file_size = os.path.getsize(upload_path)

        if FileInfo.support_image_compress(mime=mime, extension=extension):
            __handle_image(path=upload_path, mime=mime, exif=exif, name=name, extension=extension)

        return True, "", filename, mime, exif, file_size, __md5(upload_path)
    except Exception as ex:
        print(ex)
        return False, str(ex), filename, None, 0, 0, ""
    finally:
        if f is not None:
            f.close()


def __write_to_path(path, stream):
    with open(path, "wb") as f:
        buffer_size = 4096
        while f:
            stream_buffer = stream.read(buffer_size)
            if len(stream_buffer) == 0:
                f.close()
                return True
            f.write(stream_buffer)
    return False


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


def __handle_image(path, mime, exif, name, extension):
    im = Image.open(path)
    rotated = False

    quality_name = name + RGQualityName + extension
    quality_name_path = os.path.join(GlobalConfigContext.FileStore_Directory, quality_name)

    thumb_name = name + RGThumbnailName + extension
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


def perform_download(filename, at_import=False):
    """
    Perform retrieve file location for downloading via its file name.
    :param filename: file name string
    :param at_import: file in import directory
    :return: tuple of <exist flag, file actual location>
    """
    base_path = GlobalConfigContext.FileImport_Directory if at_import else GlobalConfigContext.FileStore_Directory
    find_path = os.path.join(base_path, filename)
    exist_flag = os.path.exists(find_path)
    return exist_flag, find_path


def perform_del(name):
    extension = os.path.splitext(name)[-1]
    file_pre_name = os.path.splitext(name)[0]

    path = os.path.join(GlobalConfigContext.FileStore_Directory, name)

    paths = [path]
    for name in RGExtName:
        if name.rfind('.') < 0:
            full_name = file_pre_name + name + extension
        else:
            full_name = file_pre_name + name
        p = os.path.join(GlobalConfigContext.FileStore_Directory, full_name)
        paths.append(p)

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
            exif = FileInfo.exif_data(path)
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
