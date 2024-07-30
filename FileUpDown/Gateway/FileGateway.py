#!/usr/bin/env python
# encoding: utf-8

from flask import Blueprint, abort, request, jsonify

import Gateway
from Service import FileService, RangeResponse

RestRouter = Blueprint('FileGateway', __name__, url_prefix='/file/')


@RestRouter.route('/upload/', methods=['POST'])
def handle_upload_file():
    """
    Router for file upload requests.
    多上传文件, 返回一个数组，包含上传成功的文件信息，每个元素的 key 为文件流的 key
    :return: [
        {
            'name': name,
            'path': file_path,
            'mime': mime,
            'exif': exif,
            'size': size,
            "err_msg": err_msg,
            'key': key,
        },
        ……
    ]
    """

    results = []

    re_files = request.files
    for file_key in re_files:
        __upload_with_key(file_key, results)
    return jsonify(results)


def __upload_with_key(key, res_array):
    data = request.files[key] if key in request.files else None
    flag = None
    path, mime, exif, message, size, md5 = None, None, None, None, 0, ""
    if data is not None:
        flag, message, path, mime, exif, size, md5 = FileService.perform_upload(data)
    res_array.append(__wrapper_res(data.filename, path, mime, exif, size, md5, message, flag, key))


def __wrapper_res(name, file_path, mime, exif, size, md5, err_msg, flag, key):
    return {
        'name': name,
        'path': file_path,
        'mime': mime,
        'exif': exif,
        'size': size,
        'hash': md5,
        "err_msg": err_msg,
        'flag': flag,
        'key': key,
    }


@RestRouter.route('/download/<path:filename>', methods=['GET'])
def handle_download_file(filename):
    """
    Router for file download requests.
    """
    flag, location, sub_path = FileService.perform_download(filename)
    return __actual_handle_download(filename, flag, location, sub_path)


@RestRouter.route('/download/import/<filename>', methods=['GET'])
def handle_download_import_file(filename):
    """
    Router for file download requests.
    """
    flag, location, sub_path = FileService.perform_download(filename=filename, at_import=True)
    return __actual_handle_download(filename, flag, location, sub_path)


@RestRouter.route('/download/', methods=['POST'])
def handle_download_file_post():
    """
    Router for file download requests.
    """
    # check required argument exist
    required_parameter = ["filename"]
    missing_list = Gateway.check_required_parameter(required_parameter, request.values)
    if len(missing_list) != 0:
        abort(404)
        # return "Missing required argument list: " + str(missing_list)
    filename = request.values["filename"]
    # handle download procedure
    flag, location, sub_path = FileService.perform_download(filename)
    return __actual_handle_download(filename, flag, location, sub_path)


def __actual_handle_download(filename, flag, location, sub_path):
    """
    Retrieve file from steady by controller and generate streaming response package.
    """
    if flag is False:
        abort(404)
        # return "File not exist: " + filename
    else:
        return RangeResponse.partial_response(request=request, path=location, sub_path=sub_path, filename=filename)


@RestRouter.route('/del', methods=['POST'])
def file_del():
    args = request.json
    names = args.get('names')

    results = []
    for name in names:
        result = FileService.perform_del(name)
        results.append({
            'name': name,
            'result': result
        })
    return jsonify(results)


@RestRouter.route('/info', methods=['GET'])
def file_info():
    args = request.json
    names = args.get('names')

    results = []
    for name in names:
        flag, message, path, mime, exif, size, md5 = FileService.perform_info(name)
        info = __wrapper_res(name, path, mime, exif, size, md5, message, flag, 'file')
        results.append(info)
    return jsonify(results)
