#!/usr/bin/env python
# encoding: utf-8
"""
This module handles file upload and download procedure.
"""
import os
import shutil

import magic
import uuid
import GlobalConfigContext
import logging as L
logging = L.getLogger('file')

from Service import FileInfo
import hashlib
from flask import request

RGThumbnailName = '_thumbnail'
RGQualityName = '_quality'
RGCompressCacheThumbName = '_compressCacheThumbnail'
RGCompressCacheGifName = '_compressCacheThumbnail.gif'

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
        return True, "", filename, mime, exif, file_size, __md5(upload_path)
    except Exception as ex:
        logging.err(ex)
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
        logging.error(ex, exc_info=True)
        pass
    return image, rotated


def perform_download(filename, at_import=False):
    """
    Perform retrieve file location for downloading via its file name.
    :param filename: file name string
    :param at_import: file in import directory
    :return: tuple of <exist flag, file actual location>
    """
    base_path = GlobalConfigContext.FileImport_Directory if at_import else GlobalConfigContext.FileStore_Directory
    paths = filename.split('/')
    filename = paths[0]
    find_path = os.path.join(base_path, filename)
    exist_flag = os.path.exists(find_path)

    paths.pop(0)
    sub_path = '/'.join(paths)
    
    return exist_flag, find_path, sub_path


def perform_del(name):
    path = os.path.join(GlobalConfigContext.FileStore_Directory, name)
    paths = [path, get_file_cache_base_dir(name)]

    result = True
    for path in paths:
        try:
            if os.path.exists(path):
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            else:
                pass
        except Exception as ex:
            logging.error(ex, exc_info=True)
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
        logging.error(ex, exc_info=True)
        msg = str(ex)
    finally:
        return result, msg, name, mime, exif, file_size, md5


def __md5(filename):
    m = hashlib.md5()
    with open(filename, 'rb') as f:
        for line in f:
            m.update(line)
    md5code = m.hexdigest()
    return md5code


def get_file_cache_base_dir(filename, mk_dir=False):
    basename = os.path.basename(filename)
    basename = os.path.splitext(basename)[0]
    base_dir = os.path.join(GlobalConfigContext.FileCache_Directory, basename)
    if mk_dir:
        os.makedirs(base_dir, exist_ok=True)
    return base_dir


def get_file_cache_path(filename, cache_name, mk_dir=False):
    base_dir = get_file_cache_base_dir(filename, mk_dir)
    return os.path.join(base_dir, cache_name)


def get_request_params():
    if request.is_json:
        json_data = request.get_json(silent=True)
        return json_data
    if request.args:
        return request.args
    if request.form:
        return request.form
    if request.files:
        return request.files
    return {}


def get_request_param(param_name, default=None, is_number=False):
    value = default
    if request.is_json:
        json_data = request.get_json(silent=True)
        if json_data and param_name in json_data:
            value = json_data.get(param_name, default)
    if param_name in request.args:
        value = request.args.get(param_name, default)
    if param_name in request.form:
        value = request.form.get(param_name, default)
    if param_name in request.files:
        value = request.files.get(param_name, default)
    if is_number and isinstance(value, str):
        value = float(value)
    return value
