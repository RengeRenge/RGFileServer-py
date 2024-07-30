# encoding: utf-8
from datetime import datetime
from io import BytesIO
import os
import subprocess
from urllib.parse import quote

import cv2
from PIL import Image, ImageOps, ExifTags
from flask import Response, abort, current_app
from numpy import ndarray
from Service import gifsicle
from Service import epub
from Service import FileInfo
from Service.FileService import RGCompressCacheGifName, RGCompressCacheThumbName, get_file_cache_path, get_request_param, get_request_params
import zipfile

import logging as L
logging = L.getLogger('file')


def partial_response(request, path, sub_path, filename):
    logging.info('path:%s sub_path:%s filename:%s params:%s', path, sub_path, filename, get_request_params())
    
    mime_guess = get_request_param('mime', None)
    max_size = int(get_request_param('size', 0, is_number=True))
    side = int(get_request_param('side', 0, is_number=True))
    sf = int(get_request_param('sf', 1, is_number=True))
    quality = get_request_param('quality', '0') # 数字 字符串都可能
    if quality is not None and quality.isdigit():
        quality = int(quality)

    if side == 0:
        side = None
    if isinstance(sf, int):
        sf = min(4, sf)
        sf = max(1, sf)
    if max_size == 0:
        max_size = None
    if quality == 0:
        quality = None

    name = get_request_param('name', None)
    if not name:
        name = None

    cover = get_request_param('cover', 0, is_number=True)
    if cover:
        response = cover_response(path=path, mime_guess=mime_guess, max_size=max_size, side=side, sf=sf, quality=quality)
        name = os.path.splitext(name if name else filename)[0]
        ext = response.mimetype.split('/')[-1]
        name = f'{name}.{ext}'
    elif 'Range' in request.headers:
        response = __range_stream_response(request=request, path=path, sub_path=sub_path, mime_guess=mime_guess)
        if sub_path:
            name = os.path.basename(sub_path)
    else:
        if sub_path:
            response = __full_stream_inzip_response(path=path, sub_path=sub_path, mime_guess=mime_guess)
            name = os.path.basename(sub_path)
        else:
           response = stream_response(path=path, mime_guess=mime_guess, side=side, sf=sf, max_size=max_size, quality=quality)

    disposition = filename if name is None else name
    disposition = "inline; filename*=utf-8''{}".format(quote(disposition.encode('utf8')))
    response.headers['Content-Disposition'] = disposition
    
    response.last_modified = datetime.fromtimestamp(os.path.getmtime(path))

    # Accept request with Range header
    response.headers['Accept-Ranges'] = 'bytes'
    return response


def stream_response(path, mime_guess, side, sf, max_size, quality):
    mimetype = FileInfo.mime_type(path=path, mime_guess=mime_guess)
    extension = FileInfo.extension(filename=path, mime=mimetype, mime_guess=mime_guess)
    if FileInfo.support_image_compress(mime=mimetype, extension=extension):
        try:
            is_gif = mimetype.find('gif') >= 0
            if max_size is not None and is_gif == False:
                s = side * sf if side is not None else None
                return __compress_image_quality_response(path, max_size=max_size, side=s, name=path)
            if side is not None:
                if mimetype.find('gif') >= 0: # and quality is not None and quality == 'high'
                    return __compress_gif_response(path, side, mimetype, quality=quality)
                return __compress_image_side_response(filename=path, side=side * sf, data_path=path, quality=quality)
        except Exception as ex:
            logging.error(ex, exc_info=True)
            abort(404)
    return __full_fd_response(path=path, mimetype=mimetype)


def cover_response(path, mime_guess, max_size, side, sf, quality):
    mime = FileInfo.mime_type(path=path)
    if mime.find('image') >= 0:
        return stream_response(path=path, mime_guess=mime_guess, side=side, sf=sf, max_size=max_size, quality=quality) 
    if side:
        side = side * sf
    if FileInfo.audio_type(mime=mime, mime_guess=mime_guess):
        return audio_cover_response(path=path, max_size=max_size, side=side, quality=quality)
    if FileInfo.video_type(mime=mime, mime_guess=mime_guess):
        return video_cover_response(path=path, side=side, quality=quality)
    if FileInfo.epub_type(mime=mime, mime_guess=mime_guess):
        return epub_cover_response(path=path, side=side, quality=quality)
    abort(404)


def audio_cover_response(path, max_size, side, quality):
    cache_name='@%s' % (RGCompressCacheThumbName)
    cache_path = get_file_cache_path(filename=path, cache_name=cache_name, mk_dir=True)
    if os.path.exists(cache_path):
        if max_size is not None:
            return __compress_image_quality_response(cache_path, max_size=max_size, side=side, name=path)
        if side is not None:
            return __compress_image_side_response(filename=path, side=side, data_path=cache_path, quality=quality)
        return __full_stream_response(cache_path)
    if __createAudioThumbnail(path, cache_path):
        return audio_cover_response(path, max_size, side, quality)
    abort(404)


def video_cover_response(path, side, quality):
    cache_name='@%s' % (RGCompressCacheThumbName)
    cache_path = get_file_cache_path(filename=path, cache_name=cache_name, mk_dir=True)
    if os.path.exists(cache_path):
        return __compress_image_side_response(filename=path, side=side, data_path=cache_path, quality=quality)
    if __createVideoCapture(path, cache_path):
        return __compress_image_side_response(filename=path, side=side, data_path=cache_path, quality=quality)
    abort(404)


def epub_cover_response(path, side, quality):
    with epub.open_cover(path) as fd:
        return __compress_image_side_response(filename=path, side=side, fd=fd, quality=quality)


def __createVideoCapture(path, destination):
    cap = cv2.VideoCapture(path)
    try:
        sum_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        dur = sum_frames / fps
        frame_number = min(15 if dur < 300 else 600, dur / 2) * fps
        cap.set(1, frame_number - 1)
        res, frame = cap.read()
        if res is True and frame is not None and frame.data is not None:
            frame_im = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            with Image.fromarray(frame_im) as im:
                im.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
                im = im.convert('RGB')
                im.save(destination, format='JPEG', quality=85)
                return True
    except Exception as ex:
        logging.error(ex, exc_info=True)
        return False
    finally:
        if cap is not None:
            cap.release()


def __createAudioThumbnail(path, destination):
    try:
        data = FileInfo.audio_cover(path=path)
        if data is None:
            return False
        with Image.open(BytesIO(data)) as im:
            im.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
            im = im.convert('RGB')
            im.save(destination, format='JPEG', quality=85)
            return True
    except Exception as ex:
        logging.error(ex, exc_info=True)
        return False


def __compress_image_side_response(filename, side, fd=None, data=None, data_path=None, quality=85):
    try:
        if side is None or side == 0:
            if data_path is not None:
                return __full_stream_response(data_path)
            
            cache_name='@%s' % (RGCompressCacheThumbName)
            cache_path = get_file_cache_path(filename=filename, cache_name=cache_name, mk_dir=True)
            if os.path.exists(cache_path):
                return __full_stream_response(cache_path)
            if fd is not None:
                with Image.open(fd) as im:
                    im.save(cache_path, format=im.format)
                    return __full_stream_response(cache_path)
            if data is not None:
                with open(cache_path, 'wb') as f:
                    f.write(data)
                    return __full_stream_response(cache_path)
            abort(404)

        if quality is not None:
            if isinstance(quality, str):
                if quality == 'high':
                    quality = 85
                elif quality == 'low':
                    quality = 40
                else:
                    quality = 85
            elif isinstance(quality, int):
                quality = min(int(quality), 85)
        else:
            quality = 85
        
        if data_path is not None:
            with Image.open(data_path) as im:
                return __process_image_response(im, side, quality, filename)
        if fd is not None:
            with Image.open(fd) as im:
                return __process_image_response(im, side, quality, filename)
        if data is not None:
            if isinstance(data, ndarray):
                with Image.fromarray(data) as im:
                    return __process_image_response(im, side, quality, filename)
            else:
                with Image.open(data) as im:
                    return __process_image_response(im, side, quality, filename)
        abort(404)
    except Exception as ex:
        logging.error(ex, exc_info=True)
        abort(404)


def __process_image_response(im, side, quality, filename):
    if side > im.height and side > im.width:
        side = int(max(im.height, im.width))

    cache_name='@%dx%d@quality_%d%s' % (side, side, quality, RGCompressCacheThumbName)
    cache_path = get_file_cache_path(filename=filename, cache_name=cache_name, mk_dir=True)
    if os.path.exists(cache_path):
        return __full_stream_response(cache_path)

    format = im.format
    im.thumbnail((side, side), Image.Resampling.LANCZOS)
    im = __rotate_image_if_need(image=im, exif=im.getexif())
    im.save(cache_path, format=format, quality=quality)
    return __full_stream_response(cache_path)
        
        
def __compress_gif_response(path, side, mimetype, quality):
    color = 128
    lossy = 20
    optimize = 3
    if quality is not None and isinstance(quality, str):
        if quality == 'low':
            color = 64
            lossy = 80
            optimize = 4

    with Image.open(path) as im:
        if side > im.height and side > im.width:
            side = int(max(im.height, im.width))

    cache_name='@%dx%d@color_%d@lossy_%d@optimize_%d%s' % (side, side, color, lossy, optimize, RGCompressCacheGifName)
    cache_path = get_file_cache_path(filename=path, cache_name=cache_name, mk_dir=True)
    if os.path.exists(cache_path):
        return __full_stream_response(path=cache_path, mime_guess='image/gif')
    if gifsicle.compress(path, cache_path, width=side, height=side, colors=color, lossy=lossy, optimize=optimize) == False:
        logging.error('gifsicle compress failed')
        abort(404)
    else:
        return __full_stream_response(cache_path, mimetype)


def __compress_image_quality_response(path, max_size, side, name):
    path = __compress_image_quality(path, max_size=max_size, side=side, name=name)
    return __full_stream_response(path)


def __compress_image_quality(image_path, max_size, side, name):
    """
    Compress images to a specified size
    :param image_data: image data
    :param max_size: specified size
    :param name: given '/store/photo_2024.jpg', save to '/cache/photo_2024/@102400_compressCacheThumbnail.jpeg'
    :return: new image data
    """
    

    with Image.open(image_path) as im:
        if max_size is None or max_size == 0:
            return image_path

        max_kb = max_size * 1024
        format = im.format
        
        with BytesIO() as output:
            im.save(output, format=format)
            size = output.tell()
            
            if size <= max_kb:
                return image_path

        if side is None:
            side = int(max(im.height, im.width))
        else:
            if side > im.height and side > im.width:
                side = int(max(im.height, im.width))

        cache_path = get_file_cache_path(filename=name, mk_dir=True, cache_name='@%dx%d@size_%d%s' % (side, side, max_kb, RGCompressCacheThumbName))
        
        if os.path.exists(cache_path):
            return cache_path

        with BytesIO() as img_byte_arr:
            low, high = 1, 100
            count = 0
            
            im.thumbnail((side, side), Image.Resampling.LANCZOS)
            while low < high - 1:
                mid = (low + high) // 2
                im.save(img_byte_arr, format=format, quality=mid)
                count += 1
                size = img_byte_arr.tell()
                if size > max_kb:
                    high = mid - 1
                else:
                    low = mid
                img_byte_arr.seek(0)
                img_byte_arr.truncate(0)

            logging.info('result count:%d max size:%d output size:%d', count + 1, max_kb, size)
            im.save(cache_path, format=format, quality=low)
            return cache_path


def __rotate_image_if_need(image, exif):
    if exif:
        for key in ExifTags.TAGS.keys():
            if ExifTags.TAGS[key]=='Orientation':
                if key in exif:
                    image = ImageOps.exif_transpose(image)
                break
    return image


def __get_ranges(request, file_size):
    buffer_range = request.headers.get('Range')
    group = buffer_range.split('bytes=')[-1]
    ranges = group.split(',')
    buffer_ranges = []
    logging.info('group ---------->')
    for range in ranges:
        start, length = __get_range(range=range, file_size=file_size)
        buffer_ranges.append({
            'start': start,
            'length': length
        })
        logging.info('%d - %d', start, start + length - 1)
    logging.info('group <----------')
    return buffer_ranges


def __get_range(range, file_size):
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


def __range_stream_response(request, path, sub_path, mime_guess):
    file_size = os.path.getsize(path)
    buffer_ranges = __get_ranges(request, file_size)

    buffer_range = buffer_ranges[0]
    start = buffer_range['start']
    length = buffer_range['length']

    if sub_path:
        with zipfile.ZipFile(path) as z:
            fd = z.open(sub_path)
            size = z.getinfo(sub_path).file_size
            mimetype = FileInfo.mime_type(buffer=fd, mime_guess=mime_guess)
            return __range_fd_response(fd=fd, mimetype=mimetype, size=size, start=start, length=length)
    try:
        file_size = os.path.getsize(path)
        mimetype = FileInfo.mime_type(path=path, mime_guess=mime_guess)
        with open(path, 'rb') as fd:
            return __range_fd_response(fd=fd, mimetype=mimetype, size=file_size, start=start, length=length)
    except:
        abort(404)


def __range_fd_response(fd, mimetype, size, start, length):
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


def __full_stream_response(path, mime_guess=None):
    mimetype = FileInfo.mime_type(path=path, mime_guess=mime_guess)
    return __full_fd_response(path=path, mimetype=mimetype, size=os.path.getsize(path))


def __full_stream_inzip_response(path, sub_path, mime_guess):
    try:
        with zipfile.ZipFile(path) as z:
            sub_path = sub_path.encode('gbk').decode('cp437')
            fd = z.open(sub_path)
            size = z.getinfo(sub_path).file_size
            mimetype = FileInfo.mime_type(buffer=fd, mime_guess=mime_guess)
            def completion():
                fd.close()
            return __full_fd_response(fd=fd, mimetype=mimetype, size=size, completion=completion)
    except Exception as ex:
        logging.error(ex, exc_info=True)
        abort(404)


def __full_fd_response(mimetype, fd=None, path=None, size=0, completion=None):
    completion_called = False
    def once_completion():
        nonlocal completion_called
        if completion_called:
            return
        completion_called = True
        if completion:
            completion()

    if path and os.path.exists(path):
        size = os.path.getsize(path)
        fd = open(path, 'rb')
        def __completion():
            fd.close()
            once_completion()
        return __full_fd_response(mimetype=mimetype, fd=fd, size=size, completion=__completion)
    if fd:
        try:
            if mimetype:
                if mimetype.startswith('text') or mimetype.endswith('json') or mimetype.endswith('rtf'):
                    mimetype+=';charset=UTF-8'

            response = Response(__full_fd_response_send_streaming(fd, once_completion), content_type=mimetype)
            response.headers['Content-Length'] = size
            return response
        except Exception as ex:
            logging.error(ex, exc_info=True)
            once_completion()
    abort(404)


def __full_fd_response_send_streaming(fd, completion):
    while True:
        buf = fd.read(256 * 1024)
        if not buf:
            if completion:
                completion()
            break
        yield buf
