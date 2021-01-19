# encoding: utf-8
import difflib
import mimetypes
import time
import os

import magic
import exifread
from exifread import IfdTag, Ratio
from mutagen import File


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


def mime_type(buffer=None, path=None, mime_guess=None):
    mime_parse = None
    if buffer is not None:
        mime_parse = magic.from_buffer(buffer.read(2048), mime=True)
        buffer.seek(0)
    elif path is not None:
        mime_parse = magic.from_file(filename=path, mime=True)
    else:
        assert "lack params"
    return __sure_mime(mime_parse=mime_parse, mime_guess=mime_guess)


def __sure_mime(mime_parse, mime_guess):
    """
    :param mime_parse: from magic
    :param mime_guess: from browser
    :return: mime_parse: 'audio/x-flac', mime_guess: 'audio/flac', return 'audio/flac'
    """
    if mime_guess is None:
        return mime_parse
    if mime_parse == 'application/octet-stream' or mime_parse is None:
        return mime_guess
    parse_type = mime_parse.split(sep='/')
    guess_type = mime_guess.split(sep='/')
    if parse_type[0] == guess_type[0]:
        if parse_type[-1].find(guess_type[-1]) >= 0 or guess_type[-1].find(parse_type[-1]) >= 0:
            return mime_guess
    return mime_parse


def extension(filename, mime, mime_guess):
    mime1 = mime.split(sep='/')[-1]
    mime_guess1 = mime_guess.split(sep='/')[-1]
    ext = None
    if mime1.find(mime_guess1) >= 0 or mime_guess1.find(mime1) >= 0:
        ext = __guess_extension(mime=mime, forward=mime1, filename=filename)
        if ext is None:
            ext = __guess_extension(mime=mime_guess, forward=mime_guess1, filename=filename)
    else:
        ext = __guess_extension(mime=mime, forward=mime1, filename=filename)
    if ext is None:
        ext = os.path.splitext(filename)[-1]
    if ext is None:
        ext = ""
    ext = ext.lower()
    return ext


def __guess_extension(mime, forward, filename):
    forward_ext = '.' + forward
    extensions = mimetypes.guess_all_extensions(type=mime)

    o_ext = os.path.splitext(filename)[-1]
    guess_extensions = difflib.get_close_matches(word=o_ext, possibilities=extensions, n=1)
    if len(guess_extensions) > 0:
        return guess_extensions[0]

    guess_extension = None
    guess_extensions = difflib.get_close_matches(word=forward, possibilities=extensions, n=1)
    if len(guess_extensions) > 0:
        return guess_extensions[0]
    length = 0
    for ext in extensions:
        if forward == ext or forward == forward_ext:
            return ext
        this_length = len(ext)
        if this_length > length:
            length = this_length
            guess_extension = ext
    return guess_extension


def support_image_compress(mime, extension):
    if mime.startswith('image/'):
        extension = extension.split(sep='.')[-1]
        if extension in image_support:
            return True
        return False


def exif_data(filename):
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


def audio_type(mime):
    if mime == 'application/octet-stream' or mime.startswith('audio/'):
        return True
    return False


def video_type(mime):
    if mime.startswith('video/'):
        return True
    return False


def audio_cover(path):
    audio = File(path)
    if audio is None:
        return None
    if hasattr(audio, 'pictures'):
        pictures = audio.pictures
        if pictures is not None and len(pictures) > 0:
            data = pictures[0].data
            if data is not None:
                return data
    tags = audio.tags
    return tags['APIC:'].data if 'APIC:' in tags else None
