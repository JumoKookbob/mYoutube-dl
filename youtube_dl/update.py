from __future__ import unicode_literals

import io
import json
import traceback
import hashlib
import os
import subprocess
import sys
from zipimport import zipimporter

from .compat import compat_realpath # 절대경로
from .utils import encode_compat_str

from .version import __version__


def rsa_verify(message, signature, key):
    from hashlib import sha256 # sha256 해시를 생성 (해시 = 길이가 고정된 데이터로 매핑)
    assert isinstance(message, bytes) # message가 bytes가 아니면 에러 발생
    byte_size = (len(bin(key[0])) - 2 + 8 - 1) // 8 # 바이트 사이즈
    signature = ('%x' % pow(int(signature, 16), key[1], key[0])).encode()
    signature = (byte_size * 2 - len(signature)) * b'0' + signature
    asn1 = b'3031300d060960864801650304020105000420'
    asn1 += sha256(message).hexdigest().encode()
    if byte_size < len(asn1) // 2 + 11:
        return False
    expected = b'0001' + (byte_size - len(asn1) // 2 - 3) * b'ff' + b'00' + asn1
    return expected == signature


def update_self(to_screen, verbose, opener):
    """Update the program file with the latest version from the repository"""

    UPDATE_URL = 'https://yt-dl.org/update/'
    VERSION_URL = UPDATE_URL + 'LATEST_VERSION'
    JSON_URL = UPDATE_URL + 'versions.json'
    UPDATES_RSA_KEY = (0x9d60ee4d8f805312fdb15a62f87b95bd66177b91df176765d13514a0f1754bcd2057295c5b6f1d35daa6742c3ffc9a82d3e118861c207995a8031e151d863c9927e304576bc80692bc8e094896fcf11b66f3e29e04e3a71e9a11558558acea1840aec37fc396fb6b65dc81a1c4144e03bd1c011de62e3f1357b327d08426fe93, 65537)
     # pip, setup.py, tarball 업데이트를 해야할 경우 경고를 띄운다
    if not isinstance(globals().get('__loader__'), zipimporter) and not hasattr(sys, 'frozen'): 
        to_screen('It looks like you installed youtube-dl with a package manager, pip, setup.py or a tarball. Please use that to update.')
        return 

    # Check if there is a new version
    try:
        newversion = opener.open(VERSION_URL).read().decode('utf-8').strip() # url을 열고 utf-8로 읽은 후 나눈 것 = 버전
    except Exception:
        if verbose:
            to_screen(encode_compat_str(traceback.format_exc())) # 오류 결과를 출력
        to_screen('ERROR: can\'t find the current version. Please try again later.')
        return
    if newversion == __version__:
        to_screen('youtube-dl is up-to-date (' + __version__ + ')')
        return

    # Download and check versions info
    try:
        versions_info = opener.open(JSON_URL).read().decode('utf-8') # json 파일을 utf-8으로 디코딩 후 읽기 모드로 연다
        versions_info = json.loads(versions_info) # versions_info 는 json 파일이므로 py 객체로 바꿈
    except Exception:
        if verbose: # 매개변수가 true이면
            to_screen(encode_compat_str(traceback.format_exc())) # 오류 결과를 출력
        to_screen('ERROR: can\'t obtain versions info. Please try again later.')
        return
    if 'signature' not in versions_info: 
        to_screen('ERROR: the versions file is not signed or corrupted. Aborting.') # 버전파일이 손상되거나 허가되지 않을 때
        return
    signature = versions_info['signature']
    del versions_info['signature']
    if not rsa_verify(json.dumps(versions_info, sort_keys=True).encode('utf-8'), signature, UPDATES_RSA_KEY):
        to_screen('ERROR: the versions file signature is invalid. Aborting.') # 버전 파일이 허가되지 않을때
        return

    version_id = versions_info['latest'] # 

    def version_tuple(version_str):
        return tuple(map(int, version_str.split('.'))) # 매개변수를 .으로 나눈걸 int로 매핑한 튜플
    if version_tuple(__version__) >= version_tuple(version_id): # youtube_dl이 이미 최신 버전일때
        to_screen('youtube-dl is up to date (%s)' % __version__) 
        return

    to_screen('Updating to version ' + version_id + ' ...') # 업데이트 하는 중임을 출력
    version = versions_info['versions'][version_id] 

    print_notes(to_screen, versions_info['versions'])

    # sys.executable is set to the full pathname of the exe-file for py2exe # py2exe에 대한 exe 파일의 전체 경로 이름으로 설정됨
    # though symlinks are not followed so that we need to do this manually
    # with help of realpath
    filename = compat_realpath(sys.executable if hasattr(sys, 'frozen') else sys.argv[0]) # sys.argv[0]는 python 스크립트의 명령행 인자의 0번째 

    if not os.access(filename, os.W_OK):
        to_screen('ERROR: no write permissions on %s' % filename) # 읽기 권한이 없을 때 
        return

    # Py2EXE =  파이썬 스크립트를 윈도우 실행 파일로 변환해주는 파이썬 확장 프로그램
    if hasattr(sys, 'frozen'):
        exe = filename
        directory = os.path.dirname(exe)
        if not os.access(directory, os.W_OK):
            to_screen('ERROR: no write permissions on %s' % directory)
            return

        try:
            urlh = opener.open(version['exe'][0]) # 
            newcontent = urlh.read() # urlh를 읽는다
            urlh.close()
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to download latest version')
            return

        newcontent_hash = hashlib.sha256(newcontent).hexdigest() # newcontent를 해싱한 문자열로 바꿈
        if newcontent_hash != version['exe'][1]:
            to_screen('ERROR: the downloaded file hash does not match. Aborting.') # 해시가 맞지 않을 때
            return

        try:
            with open(exe + '.new', 'wb') as outf: # 바이너리 쓰기 모드
                outf.write(newcontent) # 해싱한 문자열을 바이너리로 씀
        except (IOError, OSError):
            if verbose: # 매개변수가 true이면
                to_screen(encode_compat_str(traceback.format_exc())) # 에러 메시지를 띄움
            to_screen('ERROR: unable to write the new version') 
            return

        try:
            bat = os.path.join(directory, 'youtube-dl-updater.bat') # 디렉토리 내부 업데이터.bat 파일
            with io.open(bat, 'w') as batfile: 
                batfile.write('''
@echo off
echo Waiting for file handle to be closed ...
ping 127.0.0.1 -n 5 -w 1000 > NUL
move /Y "%s.new" "%s" > NUL
echo Updated youtube-dl to version %s.
start /b "" cmd /c del "%%~f0"&exit /b"
                \n''' % (exe, exe, version_id))

            subprocess.Popen([bat])  # Continues to run in the background
            return  # Do not show premature success messages # 주의 사함
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to overwrite current version') # 현재 버전을 덮어 쓸 수 없다는 뜻
            return

    # Zip unix package
    elif isinstance(globals().get('__loader__'), zipimporter):
        try:
            urlh = opener.open(version['bin'][0])
            newcontent = urlh.read()
            urlh.close()
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to download latest version')
            return

        newcontent_hash = hashlib.sha256(newcontent).hexdigest()
        if newcontent_hash != version['bin'][1]:
            to_screen('ERROR: the downloaded file hash does not match. Aborting.')
            return

        try:
            with open(filename, 'wb') as outf:
                outf.write(newcontent)
        except (IOError, OSError):
            if verbose:
                to_screen(encode_compat_str(traceback.format_exc()))
            to_screen('ERROR: unable to overwrite current version')
            return

    to_screen('Updated youtube-dl. Restart youtube-dl to use the new version.')


def get_notes(versions, fromVersion):
    notes = []
    for v, vdata in sorted(versions.items()):
        if v > fromVersion: 
            notes.extend(vdata.get('notes', [])) # vdata 딕셔너리에 'notes' 키를(item : 빈 리스트) 추가하고 notes에  리스트 추가 
    return notes


def print_notes(to_screen, versions, fromVersion=__version__):
    notes = get_notes(versions, fromVersion)
    if notes: # notes가 비어 있지 않으면
        to_screen('PLEASE NOTE:')
        for note in notes:
            to_screen(note)
