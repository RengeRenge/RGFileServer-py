#!/usr/bin/env python
# encoding: utf-8
"""
This package is a Blueprint of File Up/Down load Restful API router functions.
"""
from urllib.parse import quote

from flask import Blueprint, request, Response, jsonify

import Gateway
from Service import FileService

RestRouter = Blueprint('FileGateway', __name__, url_prefix='/file/')


@RestRouter.route('/upload/', methods=['POST'])
def handle_upload_file():
    """
    Router for file upload requests.
    """
    # check required argument exist
    # required_parameter = ["file"]
    # missing_list = Gateway.check_required_parameter(required_parameter, request.files)

    """
    存入文件流
    """
    # if len(missing_list) != 0:
    #     return "Missing required argument list: " + str(missing_list)
    # handle upload procedure
    name = []

    upload_with_key('file', name)
    upload_with_key('icon', name)
    upload_with_key('background', name)

    return jsonify(name)
    # res_data = {
    #     "success": flag,
    #     "msg": message,  # optional
    #     "file_path": 'file/' + file_path
    # }
    # return jsonify(res_data)
    # return "Exception occurred when uploading, " + message if flag is False \
    #     else url_for("FileGateway.handle_download_file", _external=True, filename=message)[0:-1]


def upload_with_key(key, res_array):
    data = request.files[key] if key in request.files else None
    flag = None
    if data is not None:
        flag, file_path, message, exif = FileService.perform_upload(data)
    if flag:
        res_array.append(wrapper_res(data.filename, file_path, data.mimetype, exif, message, key))


def wrapper_res(name, file_path, type, exif, err_msg, key):
    return {
        'name': name,
        'path': file_path,
        'type': type,
        'exif': exif,
        "err_msg": err_msg,
        'key': key,
    }


@RestRouter.route('/download/<filename>', methods=['GET'])
def handle_download_file(filename):
    """
    Router for file download requests.
    """
    flag, location = FileService.perform_download(filename)
    return _actual_handle_download(filename, flag, location)


@RestRouter.route('/download/import/<filename>', methods=['GET'])
def handle_download_import_file(filename):
    """
    Router for file download requests.
    """
    flag, location = FileService.perform_download(filename=filename, is_import=True)
    return _actual_handle_download(filename, flag, location)


# @RestRouter.route('/download/<filename>/', methods=['GET'])
# def handle_download_file(filename):
#     """
#     Router for file download requests.
#     """
#     flag, location = FileService.perform_download(filename)
#     return _actual_handle_download(filename, flag, location)


@RestRouter.route('/download/', methods=['POST'])
def handle_download_file_post():
    """
    Router for file download requests.
    """
    # check required argument exist
    required_parameter = ["filename"]
    missing_list = Gateway.check_required_parameter(required_parameter, request.values)
    if len(missing_list) != 0:
        return "Missing required argument list: " + str(missing_list)
    filename = request.values["filename"]
    # handle download procedure
    flag, location = FileService.perform_download(filename)
    return _actual_handle_download(filename, flag, location)


def _actual_handle_download(filename, flag, location):
    """
    Retrieve file from steady by controller and generate streaming response package.
    """
    if flag is False:
        return "File not exist: " + filename
    else:
        def send_streaming():
            with open(location, 'rb') as f:
                while True:
                    buf = f.read(10 * 1024 * 1024)
                    if not buf:
                        break
                    yield buf

        response_package = Response(send_streaming(), content_type='application/octet-stream')
        url = quote(filename.encode('utf8'))
        dis = "inline; filename*=utf-8''{}".format(url)
        response_package.headers['Content-Disposition'] = dis
        return response_package
