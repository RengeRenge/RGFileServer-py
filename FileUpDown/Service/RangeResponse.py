# encoding: utf-8
import os
from urllib.parse import quote
from flask import Response, abort
from Service import FileInfo


def partial_response(request, path, filename):
    params, mime_guess = {}, None
    if request.is_json:
        params = request.json
        mime_guess = params.get('mime', None)
    if 'audioCover' in params and int(params['audioCover']) > 0:
        return audio_cover_response(path=path)
    if 'Range' in request.headers:
        return range_stream_response(request=request, path=path, mime_guess=mime_guess)
    else:
        response = full_stream_response(path=path, mime_guess=mime_guess)
        response.headers['Content-Length'] = os.path.getsize(path)

    name = params.get('name', filename)
    name = filename if name is None else name
    dis = "inline; filename*=utf-8''{}".format(quote(name.encode('utf8')))
    response.headers['Content-Disposition'] = dis

    # Accept request with Range header
    response.headers['Accept-Ranges'] = 'bytes'
    return response


def get_ranges(request, file_size):
    buffer_range = request.headers.get('Range')
    group = buffer_range.split('bytes=')[-1]
    ranges = group.split(',')
    buffer_ranges = []
    # print('group ---------->')
    for range in ranges:
        start, length = get_range(range=range, file_size=file_size)
        buffer_ranges.append({
            'start': start,
            'length': length
        })
        # print(start, '-', start + length - 1)
    # print('group <----------')
    return buffer_ranges


def get_range(range, file_size):
    index = range.find('-')
    items = range.split('-')
    if index == 0:
        # bytes=-500
        length = int(items[-1])
        start = file_size - length
    elif index == len(range) - 1:
        # bytes=500-
        start = int(items[0])
        length = file_size - start
    else:
        # bytes=500-999
        start = int(items[0])
        length = int(items[-1]) - start + 1
    return start, length


def range_stream_response(request, path, mime_guess):
    file_size = os.path.getsize(path)
    buffer_ranges = get_ranges(request, file_size)

    buffer_range = buffer_ranges[0]
    start = buffer_range['start']
    length = buffer_range['length']
    with open(path, 'rb') as fd:
        fd.seek(start)
        read_bytes = fd.read(length)
        response = Response(
            read_bytes,
            206,  # Partial Content
            mimetype=FileInfo.mime_type(path=path, mime_guess=mime_guess),  # Content-Type must be correct
            direct_passthrough=True,  # Identity encoding
        )
        response.headers['Content-Range'] = 'bytes {0}-{1}/{2}'.format(start, start + length - 1, file_size)
        return response


def full_stream_response(path, mime_guess):
    def send_streaming():
        with open(path, 'rb') as f:
            while True:
                buf = f.read(10 * 1024 * 1024)
                if not buf:
                    break
                yield buf

    mime_type = FileInfo.mime_type(path=path, mime_guess=mime_guess)
    response = Response(send_streaming(), content_type=mime_type)
    return response


def audio_cover_response(path):
    if FileInfo.audio_type(mime=FileInfo.mime_type(path=path)):
        data = FileInfo.audio_cover(path=path)
        if data is not None:
            return Response(data, content_type='image/png')
    abort(404)
