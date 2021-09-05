# encoding: utf-8
import os
from urllib.parse import quote

import cv2
from PIL import Image
from flask import Response, abort
from Service import FileInfo
from Service.FileService import RGVideoThumbName, RGEpubThumbName
import zipfile

def partial_response(request, path, sub_path, filename):
    params, mime_guess = {}, None
    if request.is_json:
        params = request.json
        mime_guess = params.get('mime', None)
    if 'cover' in params and int(params['cover']) > 0:
        return cover_response(path=path)
    if 'Range' in request.headers:
        return range_stream_response(request=request, path=path, sub_path=sub_path, mime_guess=mime_guess)
    else:
        if sub_path is None or len(sub_path) > 0:
            response = full_stream_inzip_response(path=path, sub_path=sub_path, mime_guess=mime_guess)
        else:
            response = full_stream_response(path=path, mime_guess=mime_guess)

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


def range_stream_response(request, path, sub_path, mime_guess):
    file_size = os.path.getsize(path)
    buffer_ranges = get_ranges(request, file_size)

    buffer_range = buffer_ranges[0]
    start = buffer_range['start']
    length = buffer_range['length']

    if sub_path is None or len(sub_path) <= 0:
        file_size = os.path.getsize(path)
        mimetype = FileInfo.mime_type(path=path, mime_guess=mime_guess)
        with open(path, 'rb') as fd:
            return range_fd_response(fd=fd, mimetype=mimetype, size=file_size, start=start, length=length)
    
    try:
        with zipfile.ZipFile(path) as z:
            fd = z.open(sub_path)
            size = z.getinfo(sub_path).file_size
            mimetype = FileInfo.mime_type(buffer=fd, mime_guess=mime_guess)
            return range_fd_response(fd=fd, mimetype=mimetype, size=size, start=start, length=length)
    except:
        abort(404)


def range_fd_response(fd, mimetype, size, start, length):
    fd.seek(start)
    read_bytes = fd.read(length)
    response = Response(
        read_bytes,
        206,  # Partial Content
        mimetype=mimetype,
        direct_passthrough=True,  # Identity encoding
        )
    response.headers['Content-Range'] = 'bytes {0}-{1}/{2}'.format(start, start + length - 1, size)
    return response


def full_stream_response(path, mime_guess):
    mimetype = FileInfo.mime_type(path=path, mime_guess=mime_guess)
    return full_fd_response(path=path, mimetype=mimetype, size=os.path.getsize(path))


def full_stream_inzip_response(path, sub_path, mime_guess):
    try:
        with zipfile.ZipFile(path) as z:
            sub_path = sub_path.encode('gbk').decode('cp437')
            fd = z.open(sub_path)
            size = z.getinfo(sub_path).file_size
            mimetype = FileInfo.mime_type(buffer=fd, mime_guess=mime_guess)
            return full_fd_response(fd=fd, mimetype=mimetype, size=size)
    except Exception as ex:
        abort(404)


def full_fd_response(mimetype, size, fd=None, path=None):
    def send_streaming():
        if path is not None:
            with open(path, 'rb') as f:
                while True:
                    buf = f.read(1 * 1024 * 1024)
                    if not buf:
                        break
                    yield buf

        elif fd is not None:
            while True:
                buf = fd.read(1 * 1024 * 1024)
                if not buf:
                    break
                yield buf
    
    if mimetype is not None:
        if mimetype.startswith('text') or mimetype.endswith('json') or mimetype.endswith('rtf'):
            mimetype+=';charset=UTF-8'
    response = Response(send_streaming(), content_type=mimetype)
    response.headers['Content-Length'] = size
    return response


def cover_response(path):
    mime = FileInfo.mime_type(path=path)
    if FileInfo.audio_type(mime=mime):
        return audio_cover_response(path=path)
    if FileInfo.video_type(mime=mime):
        return video_cover_response(path=path)
    if FileInfo.epub_type(mime=mime):
        return epub_cover_response(path=path)
    abort(404)


def audio_cover_response(path):
    data = FileInfo.audio_cover(path=path)
    if data is not None:
        return Response(data, content_type='image/png')
    abort(404)


def video_cover_response(path):
    file_pre_name = os.path.splitext(path)[0]
    thumbnail_path = '%s%s' % (file_pre_name, RGVideoThumbName)
    if os.path.exists(thumbnail_path):
        return full_stream_response(path=thumbnail_path, mime_guess='image/jpeg')

    cap = cv2.VideoCapture(path)
    try:
        sum_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        dur = sum_frames / fps

        frame_number = min(15 if dur < 300 else 600, dur / 2) * fps
        cap.set(1, frame_number - 1)
        res, frame = cap.read()

        if frame is not None and frame.data is not None:
            frame_im = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(frame_im)
            im.thumbnail((1920, 1920), Image.ANTIALIAS)
            im.save(thumbnail_path, quality=70)
            return full_stream_response(path=thumbnail_path, mime_guess='image/jpeg')
        abort(404)
    except Exception as ex:
        print(ex)
        abort(404)
    finally:
        if cap is not None:
            cap.release()


def epub_cover_response(path):
    file_pre_name = os.path.splitext(path)[0]
    thumbnail_path = '%s%s' % (file_pre_name, RGEpubThumbName)
    if os.path.exists(thumbnail_path):
        return full_stream_response(path=thumbnail_path, mime_guess='image/jpeg')
    try:
        data = FileInfo.epub_cover(path=path)
        if data is not None:
            im = Image.open(data)
            im.thumbnail((1920, 1920), Image.ANTIALIAS)
            im.save(thumbnail_path, quality=70)
            return full_stream_response(path=thumbnail_path, mime_guess='image/jpeg')
        abort(404)
    except Exception as ex:
        print(ex)
        abort(404)
        