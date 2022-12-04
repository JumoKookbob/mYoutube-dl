#!/usr/bin/env python
from __future__ import unicode_literals # 상위 버전의 기능을 쓸 수 있도록 하도록 함

# Execute with
# $ python youtube_dl/__main__.py (2.6+)
# $ python -m youtube_dl          (2.7+)

import sys # 파이썬 인터프리터가 제공하는 변수와 함수를 직접 제어할 수 있게 해주는 모듈

if __package__ is None and not hasattr(sys, 'frozen'):
    # direct call of __main__.py
    import os.path 
    path = os.path.realpath(os.path.abspath(__file__)) # 파일 상대경로 출력
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

import mjuYoutube_dl

if __name__ == '__main__':
    mjuYoutube_dl.main() # 실행
