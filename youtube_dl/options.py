from __future__ import unicode_literals

import os.path # 경로명을 다룸
import optparse # 명령 줄 옵션을 구문 분석하기 위한 모듈
import re # 정규표현식 모듈 
import sys # 파이썬 인터프리터가 제공하는 변수와 함수를 직접 제어할 수 있게 해주는 모듈

from .downloader.external import list_external_downloaders # 
from .compat import (
    compat_expanduser, # 홈 디렉토리의 절대경로로 대체
    compat_get_terminal_size, # 터미널 창의 크기
    compat_getenv, # 환경변수
    compat_kwargs, # kwargs.items의 (바이트 값, 값)의 딕셔너리를 반환
    compat_shlex_split, # 변수에 대입된 shlex.split 메소드를 의미
)
from .utils import (
    preferredencoding, # 사용자 환경 설정에 따라 텍스트 데이터에 사용되는 인코딩 방식
    write_string, # 
)
from .version import __version__ # version을 가져온다


def _hide_login_info(opts): # 옵션이 private_opts일 경우 그 다음 옵션을 private로 한다
    PRIVATE_OPTS = set(['-p', '--password', '-u', '--username', '--video-password', '--ap-password', '--ap-username'])
    eqre = re.compile('^(?P<key>' + ('|'.join(re.escape(po) for po in PRIVATE_OPTS)) + ')=.+$')

    def _scrub_eq(o):
        m = eqre.match(o)
        if m:
            return m.group('key') + '=PRIVATE'
        else:
            return o

    opts = list(map(_scrub_eq, opts)) # 위의 함수와 opts를 매핑한 리스트
    for idx, opt in enumerate(opts):
        if opt in PRIVATE_OPTS and idx + 1 < len(opts): # opt가 PRI~ 에 있는 값이거나 idx + 1이 opt 길이보다 작을 때
            opts[idx + 1] = 'PRIVATE' 
    return opts


def parseOpts(overrideArguments=None): # opts(옵션들)을 분석하는 메소드
    def _readOptions(filename_bytes, default=[]): # 옵션을 읽고 디코딩된 filename_bytes를 분할한 것을 모은 것을 반환하는 메소드
        try:
            optionf = open(filename_bytes) # filename_bytes 파일을 연다
        except IOError:
            return default  # silently skip if file is not present
        try:
            ''''''
            # FIXME: https://github.com/ytdl-org/youtube-dl/commit/dfe5fa49aed02cf36ba9f743b11b0903554b5e56
            contents = optionf.read() # optionf를 읽는다
            if sys.version_info < (3,): # 파이썬 2이면
                contents = contents.decode(preferredencoding()) # contents를 환경설정에 따른 인코딩 방식으로 디코딩한다 
            res = compat_shlex_split(contents, comments=True) # contents를 큰따옴표로 묶은 부분을 하나의 단어로 취급헤서 분할
        finally:
            optionf.close()
        return res 

    def _readUserConf(): # 유저 구성파일을 만듦
        xdg_config_home = compat_getenv('XDG_CONFIG_HOME') # 환경변수
        if xdg_config_home: # xdg~가 null이 아니면
            userConfFile = os.path.join(xdg_config_home, 'youtube-dl', 'config') # 경로 저장
            if not os.path.isfile(userConfFile): # 파일이 없으면
                userConfFile = os.path.join(xdg_config_home, 'youtube-dl.conf') # 새로 만듦
        else:
            userConfFile = os.path.join(compat_expanduser('~'), '.config', 'youtube-dl', 'config') 
            if not os.path.isfile(userConfFile):
                userConfFile = os.path.join(compat_expanduser('~'), '.config', 'youtube-dl.conf')
        userConf = _readOptions(userConfFile, None) # 해당 파일을 분할한 것 (쌍따옴표까지 포함한 문자)

        if userConf is None:
            appdata_dir = compat_getenv('appdata') # appdata 환경변수를 가져옴
            if appdata_dir:
                userConf = _readOptions(
                    os.path.join(appdata_dir, 'youtube-dl', 'config'),
                    default=None)
                if userConf is None:
                    userConf = _readOptions(
                        os.path.join(appdata_dir, 'youtube-dl', 'config.txt'),
                        default=None) # 해당 파일을 분할한 것 (쌍따옴표까지 포함한 문자)

        if userConf is None: # 이게 또 none이면
            userConf = _readOptions(
                os.path.join(compat_expanduser('~'), 'youtube-dl.conf'),
                default=None)
        if userConf is None:
            userConf = _readOptions(
                os.path.join(compat_expanduser('~'), 'youtube-dl.conf.txt'),
                default=None) # 해당파일을 분할한 것

        if userConf is None: 
            userConf = []

        return userConf

    def _format_option_string(option): # 옵션 문자열을 포맷
        ''' ('-o', '--option') -> -o, --format METAVAR'''

        opts = [] # opts를 리스트로

        if option._short_opts: # 예를 들면 -o
            opts.append(option._short_opts[0]) 
        if option._long_opts: # 예를 들면 --option
            opts.append(option._long_opts[0])
        if len(opts) > 1:
            opts.insert(1, ', ') 

        if option.takes_value(): 
            opts.append(' %s' % option.metavar) 

        return ''.join(opts) # opts 리스트를 띄어쓰기 없이 문자열로 바꿈 

    def _comma_separated_values_options_callback(option, opt_str, value, parser):
        setattr(parser.values, option.dest, value.split(','))

    # No need to wrap help messages if we're on a wide console
    columns = compat_get_terminal_size().columns
    max_width = columns if columns else 80
    max_help_position = 80

    fmt = optparse.IndentedHelpFormatter(width=max_width, max_help_position=max_help_position)
    fmt.format_option_strings = _format_option_string

    kw = {
        'version': __version__,
        'formatter': fmt,
        'usage': '%prog [OPTIONS] [URL...]',
        'conflict_handler': 'resolve',
    }

    parser = optparse.OptionParser(**compat_kwargs(kw)) # 옵션파싱을 해서 딕셔너리에 저장하도록 함

    general = optparse.OptionGroup(parser, 'General Options') # 일반 옵션 그룹
    # 여기서부터
    general.add_option(
        '-h', '--help',
        action='help',
        help='이 도움말 텍스트를 인쇄하고 종료하십시오.')
    general.add_option(
        '--version',
        action='version',
        help='프로그램 버전 출력 후 종료')
    general.add_option(
        '-U', '--update',
        action='store_true', dest='update_self',
        help='이 프로그램을 최신 버전으로 업데이트합니다. 충분한 권한이 있는지 확인하십시오(필요한 경우 sudo와 함께 실행).')
    general.add_option(
        '-i', '--ignore-errors',
        action='store_true', dest='ignoreerrors', default=False,
        help='다운로드 오류를 계속합니다. 예를 들어 재생 목록에서 사용할 수 없는 비디오를 건너뜁니다.')
    general.add_option(
        '--abort-on-error',
        action='store_false', dest='ignoreerrors',
        help='오류가 발생할 경우 추가 비디오(재생 목록 또는 명령줄에서) 다운로드를 중단합니다.')
    general.add_option(
        '--dump-user-agent',
        action='store_true', dest='dump_user_agent', default=False,
        help='현재 브라우저 ID 표시')
    general.add_option(
        '--list-extractors',
        action='store_true', dest='list_extractors', default=False,
        help='지원되는 모든 추출기 나열')
    general.add_option(
        '--extractor-descriptions',
        action='store_true', dest='list_extractor_descriptions', default=False,
        help='지원되는 모든 추출기의 출력 설명')
    general.add_option(
        '--force-generic-extractor',
        action='store_true', dest='force_generic_extractor', default=False,
        help='"일반 추출기"를 사용하도록 강제 추출')
    general.add_option(
        '--default-search',
        dest='default_search', metavar='PREFIX',
        help ='"정규화되지 않은 URL에 이 접두사를 사용합니다. 예를 들어, "gvsearch2:"는 유튜브-dl "large apple"을 위해 구글 비디오에서 두 개의 비디오를 다운로드합니다. "auto" 값을 사용하여 Youtube에서 추측할 수 있습니다("auto_warning"). "error"는 단지 오류를 던집니다. 기본값 "fixup_error"는 손상된 URL을 복구하지만 검색 대신 이를 수행할 수 없는 경우 오류를 발생시킵니다."')
    general.add_option(
        '--ignore-config',
        action='store_true',
        help='구성 파일을 읽지 않습니다. '
        '글로벌 구성 파일 /etc/youtube-dl.conf에 지정된 경우: '
        '~./config/youtube-dl/config의 사용자 구성을 읽지 마십시오.'
        '(%APPDATA%/youtube-dl/config.txt on Windows)')
    general.add_option(
        '--config-location',
        dest='config_location', metavar='PATH',
        help='구성 파일의 위치. 구성에 대한 경로 또는 구성 파일이 포함된 디렉토리')
    general.add_option(
        '--flat-playlist',
        action='store_const', dest='extract_flat', const='in_playlist',
        default=False,
        help='재생 목록의 비디오를 추출하지 않고 나열만 합니다.')
    general.add_option(
        '--mark-watched',
        action='store_true', dest='mark_watched', default=False,
        help='시청한 동영상 표시 (오직 YouTube에서만)')
    general.add_option(
        '--no-mark-watched',
        action='store_false', dest='mark_watched', default=False,
        help='시청한 동영상을 표시하지않음(오직 YouTube에서만)')
    general.add_option(
        '--no-color', '--no-colors',
        action='store_true', dest='no_color',
        default=False,
        help='출력에서 색상 코드를 내보내지 않음')

    network = optparse.OptionGroup(parser, 'Network Options')
    network.add_option(
        '--proxy', dest='proxy',
        default=None, metavar='URL',
        help='지정된 HTTP/HTTPS/SOCKS 프록시를 사용합니다. '
             'SOKS 프록시를 사용하려면 적절한 구성표를 지정하십시오.'
             '예를 들어 socks5://127.0.0.1:1080/. 빈 문자열은 지나칩니다 (--proxy "") '
             '직접 연결하기 위함')
    network.add_option(
        '--socket-timeout',
        dest='socket_timeout', type=float, default=None, metavar='SECONDS',
        help='포기하기 전에 기다리는 시간(초 단위)')
    network.add_option(
        '--source-address',
        metavar='IP', dest='source_address', default=None,
        help='바인딩할 클라이언트 측 IP 주소',
    )
    network.add_option(
        '-4', '--force-ipv4',
        action='store_const', const='0.0.0.0', dest='source_address',
        help='IPv4를 통해 모든 연결 만들기',
    )
    network.add_option(
        '-6', '--force-ipv6',
        action='store_const', const='::', dest='source_address',
        help='IPv6를 통해 모든 연결 만들기',
    )

    geo = optparse.OptionGroup(parser, 'Geo Restriction')
    geo.add_option(
        '--geo-verification-proxy',
        dest='geo_verification_proxy', default=None, metavar='URL',
        help='이 프록시를 사용하여 일부 지역 제한 사이트의 IP 주소를 확인합니다. '
        '--proxy로 지정된 기본 프록시(또는 옵션이 존재하지 않는 경우)가 실제 다운로드에 사용됩니다.')    
    geo.add_option(
        '--cn-verification-proxy',
        dest='cn_verification_proxy', default=None, metavar='URL',
        help=optparse.SUPPRESS_HELP)
    geo.add_option(
        '--geo-bypass',
        action='store_true', dest='geo_bypass', default=True,
        help='forwarded-HTTP 헤더를 통해 지리적 제한을 무시합니다.')
    geo.add_option(
        '--no-geo-bypass',
        action='store_false', dest='geo_bypass', default=True,
        help='forwarded-HTTP 헤더를 통해 지리적 제한을 무시하지않습니다.')
    geo.add_option(
        '--geo-bypass-country', metavar='CODE',
        dest='geo_bypass_country', default=None,
        help='명시적으로 제공된 ISO 3166-2 국가 코드로 지리적 제한 적용')
    geo.add_option(
        '--geo-bypass-ip-block', metavar='IP_BLOCK',
        dest='geo_bypass_ip_block', default=None,
        help='CIDR 표기법으로 명시적으로 제공된 IP 블록으로 지리적 제한 적용')
    selection = optparse.OptionGroup(parser, 'Video Selection')
    selection.add_option(
        '--playlist-start',
        dest='playliststart', metavar='NUMBER', default=1, type=int,
        help='시작할 재생 목록 비디오(기본값: %default)')
    selection.add_option(
        '--playlist-end',
        dest='playlistend', metavar='NUMBER', default=None, type=int,
        help='종료할 재생 목록 비디오(기본값은 마지막)')
    selection.add_option(
        '--playlist-items',
        dest='playlist_items', metavar='ITEM_SPEC', default=None,
        help='다운로드할 비디오 항목을 나열합니다. 재생 목록에서 색인화된 비디오 1, 2, 5, 8을 다운로드하려면 "--playlist-items 1, 2, 5, 8"과 같이 쉼표로 구분하여 재생 목록에 있는 비디오의 색인을 지정합니다. "--playlist-items 1-3,7,10-13" 범위를 지정할 수 있습니다. 그러면 인덱스 1,2,3,7,10,11,12,13에서 비디오가 다운로드됩니다."')
    selection.add_option(
        '--match-title',
        dest='matchtitle', metavar='REGEX',
        help='일치하는 제목만 다운로드(대소문자를 구분하지 않는 정규식 또는 영숫자 하위 문자열)')
    selection.add_option(
        '--reject-title',
        dest='rejecttitle', metavar='REGEX',
        help='대소문자를 구분하지 않는 정규식 또는 영숫자 하위 문자열) 일치하는 제목에 대한 다운로드 건너뛰기')
    selection.add_option(
        '--max-downloads',
        dest='max_downloads', metavar='NUMBER', type=int, default=None,
        help='NUMBER 파일 다운로드 후 중단')
    selection.add_option(
        '--min-filesize',
        metavar='SIZE', dest='min_filesize', default=None,
        help='SIZE(예: 50k 또는 44.6m)보다 작은 비디오는 다운로드하지 않음)')
    selection.add_option(
        '--max-filesize',
        metavar='SIZE', dest='max_filesize', default=None,
        help='SIZE(예: 50k 또는 44.6m)보다 큰 비디오는 다운로드하지 마십시오.')
    selection.add_option(
        '--date',
        metavar='DATE', dest='date', default=None,
        help='이 날짜에 업로드된 동영상만 다운로드')
    selection.add_option(
        '--datebefore',
        metavar='DATE', dest='datebefore', default=None,
        help='이 날짜 이전에 업로드된 동영상만 다운로드(즉, 포함)')
    selection.add_option(
        '--dateafter',
        metavar='DATE', dest='dateafter', default=None,
        help='이 날짜 이후에 업로드된 동영상만 다운로드(즉, 포함)')
    selection.add_option(
        '--min-views',
        metavar='COUNT', dest='min_views', default=None, type=int,
        help='COUNT 보기보다 작은 동영상은 다운로드하지 마십시오.')
    selection.add_option(
        '--max-views',
        metavar='COUNT', dest='max_views', default=None, type=int,
        help='COUNT 뷰 이상의 비디오를 다운로드하지 마십시오.')
    selection.add_option(
        '--match-filter',
        metavar='FILTER', dest='match_filter', default=None,
        help=(
            '일반 비디오 필터. '
            'key를 지정하십시오(사용 가능한 키 목록은 "OUTPUT TEMPLE" 참조).'
            'key가 있는지 확인하십시오.'
            '!key가 존재하지 않는지 확인하기 위한 key'
            ' key > NUMBER("comment_count > 12"와 마찬가지로) 함께 작동합니다.'
            '>=, <, <=, !=, =) 숫자와 비교하기 위해, '
            'key = \'LITERAL\' (예: "messager = \'Mike Smith\")도 !=와 함께 작동합니다.)'
            '문자열과 일치시키다'
            '여러 개의 일치 항목이 필요합니다. '
            '알 수 없는 값은 다음을 제외한다.'
            '연산자 뒤에 물음표(?)를 붙입니다. '
            '예를 들어, '
            '보다 더 좋아하는 비디오만 일치시키는 것'
            '100번 이상 미움을 50번 미만(또는 미움직임'
            '지정된 서비스에서는 기능을 사용할 수 없습니다.'
            '또한 설명이 있습니다. --match-filter를 사용하십시오.'
            '"like_count > 100 & havior_count <? 50 & description" .'
        ))
    selection.add_option(
        '--no-playlist',
        action='store_true', dest='noplaylist', default=False,
        help='URL이 비디오 및 재생 목록을 참조하는 경우 재생 목록을 다운로드합니다.')
    selection.add_option(
        '--yes-playlist',
        action='store_false', dest='noplaylist', default=False,
        help='URL이 비디오 및 재생 목록을 참조하는 경우 재생 목록을 다운로드합니다.') 
    selection.add_option(
        '--age-limit',
        metavar='YEARS', dest='age_limit', default=None, type=int,
        help='특정 연령에 적합한 비디오만 다운로드')
    selection.add_option(
        '--download-archive', metavar='FILE',
        dest='download_archive',
        help='보관 파일에 나열되지 않은 비디오만 다운로드합니다. 다운로드한 모든 동영상의 ID를 기록합니다.')    
    selection.add_option(
        '--include-ads',
        dest='include_ads', action='store_true',
        help='광고도 다운로드 합니다(실험적)')

    authentication = optparse.OptionGroup(parser, 'Authentication Options')
    authentication.add_option(
        '-u', '--username',
        dest='username', metavar='USERNAME',
        help='이 계정 ID로 로그인')
    authentication.add_option(
        '-p', '--password',
        dest='password', metavar='PASSWORD',
        help='계정 암호. 이 옵션이 빠지면 youtube-dl이 대화형으로 질문할 것이다.')
    authentication.add_option(
        '-2', '--twofactor',
        dest='twofactor', metavar='TWOFACTOR',
        help='이중인증코드')
    authentication.add_option(
        '-n', '--netrc',
        action='store_true', dest='usenetrc', default=False,
        help='.netrc 인증 데이터 사용')
    authentication.add_option(
        '--video-password',
        dest='videopassword', metavar='PASSWORD',
        help='비디오 암호(vimeo, youku)')

    adobe_pass = optparse.OptionGroup(parser, 'Adobe Pass Options')
    adobe_pass.add_option(
        '--ap-mso',
        dest='ap_mso', metavar='MSO',
        help='Adobe Pass 다중 시스템 운영자(TV 제공자) 식별자, 사용 가능한 MSO 목록에 --ap-list-mso를 사용하십시오.')    
    adobe_pass.add_option(
        '--ap-username',
        dest='ap_username', metavar='USERNAME',
        help='다중 시스템 운영자 계정 로그인')
    adobe_pass.add_option(
        '--ap-password',
        dest='ap_password', metavar='PASSWORD',
        help='다중 시스템 운영자 계정 암호입니다. 이 옵션이 빠지면 youtube-dl이 대화형으로 질문할 것이다.')
    adobe_pass.add_option(
        '--ap-list-mso',
        action='store_true', dest='ap_list_mso', default=False,
        help='지원되는 모든 다중 시스템 연산자 나열')

    video_format = optparse.OptionGroup(parser, 'Video Format Options')
    video_format.add_option(
        '-f', '--format',
        action='store', dest='format', metavar='FORMAT', default=None,
        help='비디오 형식 코드, 모든 정보는 "FORMAT SELECTION"을 참조하십시오.')
    video_format.add_option(
        '--all-formats',
        action='store_const', dest='format', const='all',
        help='사용 가능한 모든 비디오 형식 다운로드')
    video_format.add_option(
        '--prefer-free-formats',
        action='store_true', dest='prefer_free_formats', default=False,
        help='특정 비디오 형식을 요청하지 않는 한 무료 비디오 형식 선호')
    video_format.add_option(
        '-F', '--list-formats',
        action='store_true', dest='listformats',
        help='요청된 비디오의 모든 형식 나열')
    video_format.add_option(
        '--youtube-include-dash-manifest',
        action='store_true', dest='youtube_include_dash_manifest', default=True,
        help=optparse.SUPPRESS_HELP)
    video_format.add_option(
        '--youtube-skip-dash-manifest',
        action='store_false', dest='youtube_include_dash_manifest',
        help='YouTube 동영상에서 DASH 매니페스트 및 관련 데이터를 다운로드하지 마십시오.')
    video_format.add_option(
        '--merge-output-format',
        action='store', dest='merge_output_format', metavar='FORMAT', default=None,
        help=(
            '병합이 필요한 경우(예: 최상의 비디오 + 최상의 오디오),'
            '지정된 컨테이너 형식으로 출력합니다. mkv, mp4, ogg, webm, flv 중 하나.'
            '병합이 필요 없는 경우 무시됨'))

    subtitles = optparse.OptionGroup(parser, 'Subtitle Options')
    subtitles.add_option(
        '--write-sub', '--write-srt',
        action='store_true', dest='writesubtitles', default=False,
        help='부제 파일 쓰기')
    subtitles.add_option(
        '--write-auto-sub', '--write-automatic-sub',
        action='store_true', dest='writeautomaticsub', default=False,
        help='자동 생성된 자막 파일 작성(YouTube 전용)')
    subtitles.add_option(
        '--all-subs',
        action='store_true', dest='allsubtitles', default=False,
        help='비디오의 사용 가능한 모든 자막을 다운로드하십시오.')
    subtitles.add_option(
        '--list-subs',
        action='store_true', dest='listsubtitles', default=False,
        help='비디오에 사용할 수 있는 모든 자막 나열')
    subtitles.add_option(
        '--sub-format',
        action='store', dest='subtitlesformat', metavar='FORMAT', default='best',
        help='부제 형식: "srt" 또는 "ass/srt/best"와 같은 형식 기본 설정을 사용합니다.')
    subtitles.add_option(
        '--sub-lang', '--sub-langs', '--srt-lang',
        action='callback', dest='subtitleslangs', metavar='LANGS', type='str',
        default=[], callback=_comma_separated_values_options_callback,
        help='다운로드할 자막의 언어(선택사항), 사용 가능한 언어 태그에는 --list-subs를 사용합니다.')

    downloader = optparse.OptionGroup(parser, 'Download Options')
    downloader.add_option(
        '-r', '--limit-rate', '--rate-limit',
        dest='ratelimit', metavar='RATE',
        help='최대 다운로드 속도(초당 바이트 수)(예: 50K 또는 4).2M)')
    downloader.add_option(
        '-R', '--retries',
        dest='retries', metavar='RETRIES', default=10,
        help='재시도 횟수(기본값은 %default) 또는 "무한"입니다.')
    downloader.add_option(
        '--fragment-retries',
        dest='fragment_retries', metavar='RETRIES', default=10,
        help='프래그먼트에 대한 재시도 횟수(기본값: %default) 또는 "재시도 횟수"(DASH, hlsnative 및 ISM')
    downloader.add_option(
        '--skip-unavailable-fragments',
        action='store_true', dest='skip_unavailable_fragments', default=True,
        help='사용할 수 없는 조각(DASH, hlsnative 및 ISM) 건너뛰기')
    downloader.add_option(
        '--abort-on-unavailable-fragment',
        action='store_false', dest='skip_unavailable_fragments',
        help='일부 조각을 사용할 수 없는 경우 다운로드를 중단합니다.')
    downloader.add_option(
        '--keep-fragments',
        action='store_true', dest='keep_fragments', default=False,
        help='다운로드가 완료된 후에도 디스크에 다운로드된 조각을 유지합니다. 조각은 기본적으로 지워집니다.')
    downloader.add_option(
        '--buffer-size',
        dest='buffersize', metavar='SIZE', default='1024',
        help='다운로드 버퍼 크기(예: 1024 또는 16K)(기본값은 %default)')
    downloader.add_option(
        '--no-resize-buffer',
        action='store_true', dest='noresizebuffer', default=False,
        help='버퍼 크기를 자동으로 조정하지 마십시오. 기본적으로 버퍼 크기는 초기 값 SIZE에서 자동으로 크기가 조정됩니다.')
    downloader.add_option(
        '--http-chunk-size',
        dest='http_chunk_size', metavar='SIZE', default=None,
        help='청크 기반 HTTP 다운로드를 위한 청크 크기(예: 10485760 또는 10M)(기본값은 비활성화됨). '
             '웹 서버에 의해 부과되는 대역폭 조절을 우회하는 데 유용할 수 있음(실험적)')
    downloader.add_option(
        '--test',
        action='store_true', dest='test', default=False,
        help=optparse.SUPPRESS_HELP)
    downloader.add_option(
        '--playlist-reverse',
        action='store_true',
        help='재생 목록 비디오를 역순으로 다운로드')
    downloader.add_option(
        '--playlist-random',
        action='store_true',
        help='재생 목록 비디오를 임의 순서로 다운로드')
    downloader.add_option(
        '--xattr-set-filesize',
        dest='xattr_set_filesize', action='store_true',
        help='파일 x 속성 ytdl을 설정합니다.예상 파일 크기의 파일 크기')
    downloader.add_option(
        '--hls-prefer-native',
        dest='hls_prefer_native', action='store_true', default=None,
        help='fmpeg 대신 네이티브 HLS 다운로더 사용')
    downloader.add_option(
        '--hls-prefer-ffmpeg',
        dest='hls_prefer_native', action='store_false', default=None,
        help='네이티브 HLS 다운로더 대신 ffmpeg 사용')
    downloader.add_option(
        '--hls-use-mpegts',
        dest='hls_use_mpegts', action='store_true',
        help='HLS 비디오에 megts 컨테이너 사용, 재생 허용'
             '다운로드하는 동안 비디오(일부 플레이어는 재생할 수 없을 수 있음)')
    downloader.add_option(
        '--external-downloader',
        dest='external_downloader', metavar='COMMAND',
        help='지정된 외부 다운로드기를 사용합니다. '
             '현재 %s을(를) 지원합니다.' % ','.join(list_external_downloaders()))
    downloader.add_option(
        '--external-downloader-args',
        dest='external_downloader_args', metavar='ARGS',
        help='외부 다운로드자에게 다음과 같은 주장을 전달합니다.')

    workarounds = optparse.OptionGroup(parser, 'Workarounds')
    workarounds.add_option(
        '--encoding',
        dest='encoding', metavar='ENCODING',
        help='지정된 인코딩 강제 적용(실험)')
    workarounds.add_option(
        '--no-check-certificate',
        action='store_true', dest='no_check_certificate', default=False,
        help='HTTPS 인증서 유효성 검사 억제')
    workarounds.add_option(
        '--prefer-insecure',
        '--prefer-unsecure', action='store_true', dest='prefer_insecure',
        help='암호화되지 않은 연결을 사용하여 동영상에 대한 정보를 검색합니다. (현재 YouTube에서만 지원됨)')
    workarounds.add_option(
        '--user-agent',
        metavar='UA', dest='user_agent',
        help='사용자 지정 사용자 에이전트 지정')
    workarounds.add_option(
        '--referer',
        metavar='URL', dest='referer', default=None,
        help='사용자 지정 참조인을 지정합니다. 비디오 액세스가 하나의 도메인으로 제한된 경우 사용합니다.',
    )
    workarounds.add_option(
        '--add-header',
        metavar='FIELD:VALUE', dest='headers', action='append',
        help='사용자 지정 HTTP 헤더와 해당 값을 콜론 \':\'으로 구분하여 지정합니다. 이 옵션을 여러 번 사용할 수 있습니다.',
    )
    workarounds.add_option(
        '--bidi-workaround',
        dest='bidi_workaround', action='store_true',
        help='양방향 텍스트 지원이 없는 단말기를 해결합니다. PATH에서 bidiv 또는 fribidi 실행 파일 필요')
    workarounds.add_option(
        '--sleep-interval', '--min-sleep-interval', metavar='SECONDS',
        dest='sleep_interval', type=float,
        help=(
            '단독으로 사용할 때 각 다운로드 전에 절전 모드로 전환하는 시간(초)'
            '또는 각 다운로드 전 무작위 절전 범위의 하한'
            '와 함께 사용할 경우 (최소 절전 가능 시간(초))'
            '최대 수면 시간'))
    workarounds.add_option(
        '--max-sleep-interval', metavar='SECONDS',
        dest='max_sleep_interval', type=float,
        help=(
            '각 다운로드 전 무작위 절전 범위의 상한'
            '(최대 절전 시간(초)입니다. 만 사용해야 합니다.'
            '최소한의 수면 시간과 함께.'))

    verbosity = optparse.OptionGroup(parser, 'Verbosity / Simulation Options')
    verbosity.add_option(
        '-q', '--quiet',
        action='store_true', dest='quiet', default=False,
        help='저소음 모드 활성화')
    verbosity.add_option(
        '--no-warnings',
        dest='no_warnings', action='store_true', default=False,
        help='경고를 무시하기')
    verbosity.add_option(
        '-s', '--simulate',
        action='store_true', dest='simulate', default=False,
        help='비디오를 다운로드하지 않고 디스크에 아무것도 쓰지 않습니다.')
    verbosity.add_option(
        '--skip-download',
        action='store_true', dest='skip_download', default=False,
        help='비디오 다운로드 안 함')
    verbosity.add_option(
        '-g', '--get-url',
        action='store_true', dest='geturl', default=False,
        help='시뮬레이션, 조용하지만 URL 출력')
    verbosity.add_option(
        '-e', '--get-title',
        action='store_true', dest='gettitle', default=False,
        help='시뮬레이션, 조용하지만 제목 출력')
    verbosity.add_option(
        '--get-id',
        action='store_true', dest='getid', default=False,
        help='시뮬레이션, 조용하지만 id 출력')
    verbosity.add_option(
        '--get-thumbnail',
        action='store_true', dest='getthumbnail', default=False,
        help='시뮬레이션, 조용하지만 썸네일 URL 출력')
    verbosity.add_option(
        '--get-description',
        action='store_true', dest='getdescription', default=False,
        help='시뮬레이션, 조용하지만 영상 설명 출력')
    verbosity.add_option(
        '--get-duration',
        action='store_true', dest='getduration', default=False,
        help='시뮬레이션, 조용하지만 영상 길이 출력')
    verbosity.add_option(
        '--get-filename',
        action='store_true', dest='getfilename', default=False,
        help='시뮬레이션, 조용하지만 파일 이름 출력')
    verbosity.add_option(
        '--get-format',
        action='store_true', dest='getformat', default=False,
        help='시뮬레이션, 조용하지만 포맷 출력')
    verbosity.add_option(
        '-j', '--dump-json',
        action='store_true', dest='dumpjson', default=False,
        help='조용하지만 JSON 정보를 인쇄합니다. 사용 가능한 키에 대한 설명은 "OUTPUT TEMPLE"을 참조하십시오.')
    verbosity.add_option(
        '-J', '--dump-single-json',
        action='store_true', dest='dump_single_json', default=False,
        help='각 명령줄 인수에 대한 JSON 정보를 시뮬레이션하고 조용하지만 인쇄합니다. URL이 재생 목록을 참조하는 경우 전체 재생 목록 정보를 한 줄로 덤프합니다.')    
    verbosity.add_option(
        '--print-json',
        action='store_true', dest='print_json', default=False,
        help='조용히 하고 JSON으로 비디오 정보를 인쇄하십시오(비디오가 다운로드 중임).',    )
    verbosity.add_option(
        '--newline',
        action='store_true', dest='progress_with_newline', default=False,
        help='진행 표시줄을 새 줄로 출력')
    verbosity.add_option(
        '--no-progress',
        action='store_true', dest='noprogress', default=False,
        help='진행 표시줄을 인쇄하지 않음')
    verbosity.add_option(
        '--console-title',
        action='store_true', dest='consoletitle', default=False,
        help='콘솔 제목 표시줄에 진행률 표시')
    verbosity.add_option(
        '-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='다양한 디버깅 정보 인쇄')
    verbosity.add_option(
        '--dump-pages', '--dump-intermediate-pages',
        action='store_true', dest='dump_intermediate_pages', default=False,
        help='base64를 사용하여 인코딩된 다운로드된 페이지를 인쇄하여 문제를 디버깅합니다(매우 상세).')
    verbosity.add_option(
        '--write-pages',
        action='store_true', dest='write_pages', default=False,
        help='문제를 디버깅하기 위해 다운로드한 중간 페이지를 현재 디렉터리의 파일에 기록')
    verbosity.add_option(
        '--youtube-print-sig-code',
        action='store_true', dest='youtube_print_sig_code', default=False,
        help=optparse.SUPPRESS_HELP)
    verbosity.add_option(
        '--print-traffic', '--dump-headers',
        dest='debug_printtraffic', action='store_true', default=False,
        help='전송된 HTTP 트래픽 표시 및 읽기')
    verbosity.add_option(
        '-C', '--call-home',
        dest='call_home', action='store_true', default=False,
        help='유튜브-dl 서버에 문의하여 디버깅하십시오.')
    verbosity.add_option(
        '--no-call-home',
        dest='call_home', action='store_false', default=False,
        help='debugging을 위해 youtube-dl 서버에 접속하지 마십시오.')

    filesystem = optparse.OptionGroup(parser, 'Filesystem Options')
    filesystem.add_option(
        '-a', '--batch-file',
        dest='batchfile', metavar='FILE',
        help="다운로드할 URL('-' for stdin)을 포함하는 파일로, 한 줄에 하나의 URL을 입력합니다. "
             "'#', ';' 또는 ']'로 시작하는 줄은 주석으로 간주되어 무시됩니다.")
    filesystem.add_option(
        '--id', default=False,
        action='store_true', dest='useid', help='파일 이름에 비디오 ID만 사용')
    filesystem.add_option(
        '-o', '--output',
        dest='outtmpl', metavar='TEMPLATE',
        help=('출력 파일 이름 템플릿, 모든 정보는 "OUTPUT TEMPLE"을 참조하십시오.'))
    filesystem.add_option(
        '--output-na-placeholder',
        dest='outtmpl_na_placeholder', metavar='PLACEHOLDER', default='NA',
        help='출력 파일 이름 템플릿에서 사용할 수 없는 메타 필드에 대한 자리 표시자 값(기본값: "%default"')    
    filesystem.add_option(
        '--autonumber-size',
        dest='autonumber_size', metavar='NUMBER', type=int,
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '--autonumber-start',
        dest='autonumber_start', metavar='NUMBER', default=1, type=int,
        help='%(자동 번호)의 시작 값을 지정합니다(기본값은 %default)')
    filesystem.add_option(
        '--restrict-filenames',
        action='store_true', dest='restrictfilenames', default=False,
        help='파일 이름을 ASCII 문자로만 제한하고 파일 이름의 "&" 및 공백은 사용하지 마십시오.')
    filesystem.add_option(
        '-A', '--auto-number',
        action='store_true', dest='autonumber', default=False,
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '-t', '--title',
        action='store_true', dest='usetitle', default=False,
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '-l', '--literal', default=False,
        action='store_true', dest='usetitle',
        help=optparse.SUPPRESS_HELP)
    filesystem.add_option(
        '-w', '--no-overwrites',
        action='store_true', dest='nooverwrites', default=False,
        help='파일 덮어쓰기 안 함')
    filesystem.add_option(
        '-c', '--continue',
        action='store_true', dest='continue_dl', default=True,
        help='부분적으로 다운로드된 파일을 강제로 다시 시작합니다. 기본적으로 유튜브-dl은 가능하다면 다운로드를 재개할 것이다.')
    filesystem.add_option(
        '--no-continue',
        action='store_false', dest='continue_dl',
        help='부분적으로 다운로드된 파일을 다시 시작하지 않음(처음부터 다시 시작됨)')
    filesystem.add_option(
        '--no-part',
        action='store_true', dest='nopart', default=False,
        help='.part 파일 사용 안 함 - 출력 파일에 직접 쓰기')
    filesystem.add_option(
        '--no-mtime',
        action='store_false', dest='updatetime', default=True,
        help='마지막으로 수정한 헤더를 사용하여 파일 수정 시간을 설정하지 마십시오.')
    filesystem.add_option(
        '--write-description',
        action='store_true', dest='writedescription', default=False,
        help='.description 파일에 비디오 설명 쓰기')
    filesystem.add_option(
        '--write-info-json',
        action='store_true', dest='writeinfojson', default=False,
        help='.info.json 파일에 비디오 메타데이터 쓰기')
    filesystem.add_option(
        '--write-annotations',
        action='store_true', dest='writeannotations', default=False,
        help='비디오 주석을 .documentations.xml 파일에 기록')
    filesystem.add_option(
        '--load-info-json', '--load-info',
        dest='load_info_filename', metavar='FILE',
        help='JSON 파일("--write-info-json" 옵션으로 생성)')
    filesystem.add_option(
        '--cookies',
        dest='cookiefile', metavar='FILE',
        help='쿠키를 읽고 쿠키 병을 덤프할 파일')
    filesystem.add_option(
        '--cache-dir', dest='cachedir', default=None, metavar='DIR',
        help='you-dl이 다운로드한 일부 정보를 영구적으로 저장할 수 있는 파일 시스템의 위치입니다. 기본적으로 $XDG_CACHE_HOME/youtube-dl 또는 ~.cache/youtube-dl. 현재는 (서명이 난독화된 동영상의 경우) YouTube 플레이어 파일만 캐시되지만 변경될 수 있습니다.')
    filesystem.add_option(
        '--no-cache-dir', action='store_const', const=False, dest='cachedir',
        help='파일 시스템 캐싱 사용 안 함')
    filesystem.add_option(
        '--rm-cache-dir',
        action='store_true', dest='rm_cachedir',
        help='모든 파일 시스템 캐시 파일 삭제')

    thumbnail = optparse.OptionGroup(parser, 'Thumbnail Options')
    thumbnail.add_option(
        '--write-thumbnail',
        action='store_true', dest='writethumbnail', default=False,
        help='디스크에 섬네일 이미지 쓰기')
    thumbnail.add_option(
        '--write-all-thumbnails',
        action='store_true', dest='write_all_thumbnails', default=False,
        help='모든 섬네일 이미지 형식을 디스크에 기록')
    thumbnail.add_option(
        '--list-thumbnails',
        action='store_true', dest='list_thumbnails', default=False,
        help='사용 가능한 모든 섬네일 형식 시뮬레이션 및 나열')

    postproc = optparse.OptionGroup(parser, 'Post-processing Options')
    postproc.add_option(
        '-x', '--extract-audio',
        action='store_true', dest='extractaudio', default=False,
        help='비디오 파일을 오디오 전용 파일로 변환(ffmpeg/avconv 및 ffprobe/avprobe)')
    postproc.add_option(
        '--audio-format', metavar='FORMAT', dest='audioformat', default='best',
        help='오디오 형식 지정: "best", "aac", "flac", "mp3", "m4a", "opus", "vorbis" 또는 "flac"; 기본값으로 "%default", -x"가 없으면 효과 없음')
    postproc.add_option(
        '--audio-quality', metavar='QUALITY',
        dest='audioquality', default='5',
        help='fmpeg/avconv 오디오 품질을 지정하고, VBR에 대해 0(숫자)과 9(숫자) 사이의 값을 삽입하거나 128K(기본값 %기본값)와 같은 특정 비트 전송률을 삽입하십시오.')
    postproc.add_option(
        '--recode-video',
        metavar='FORMAT', dest='recodevideo', default=None,
        help='필요한 경우 비디오를 다른 형식으로 인코딩합니다(현재 지원되는 형식: mp4|flv|ogg|webm|httpsv|avi).')
    postproc.add_option(
        '--postprocessor-args',
        dest='postprocessor_args', metavar='ARGS',
        help='후처리기에 이 인수를 제공합니다(후처리가 필요한 경우).')
    postproc.add_option(
        '-k', '--keep-video',
        action='store_true', dest='keepvideo', default=False,
        help='후 처리 후에도 비디오 파일을 디스크에 보관합니다. 기본적으로 비디오는 지워집니다.')
    postproc.add_option(
        '--no-post-overwrites',
        action='store_true', dest='nopostoverwrites', default=False,
        help='삭제 후 파일을 덮어쓰지 않습니다. 삭제 후 파일은 기본적으로 덮어씁니다.')
    postproc.add_option(
        '--embed-subs',
        action='store_true', dest='embedsubtitles', default=False,
        help='비디오에 자막이 내장되어 있습니다(mp4, webm 및 mkv 비디오에만 해당).')
    postproc.add_option(
        '--embed-thumbnail',
        action='store_true', dest='embedthumbnail', default=False,
        help='오디오에 커버 아트로 썸네일 포함')
    postproc.add_option(
        '--add-metadata',
        action='store_true', dest='addmetadata', default=False,
        help='비디오 파일에 메타데이터 쓰기')
    postproc.add_option(
        '--metadata-from-title',
        metavar='FORMAT', dest='metafromtitle',
        help='노래 제목/아티스트와 같은 추가 메타데이터를 비디오 제목에서 구문 분석합니다. '
             '형식 구문은 --output과 동일합니다. 명명된 캡처 그룹이 있는 정규식을 사용할 수도 있습니다. '
             '파싱된 매개변수가 기존 값을 대체합니다. '
             '예시: --metadata-from-title "%(artist)s - %(title)s" "Coldplay - Paradise"와 같은 제목과 일치합니다. '
             '예시 (regex): --metadata-from-title "(?P<artist>.+?) - (?P<title>.+)"')
    postproc.add_option(
        '--xattrs',
        action='store_true', dest='xattrs', default=False,
        help='비디오 파일에 메타데이터 쓰기\"의 xattrs(더블린 코어 및 xdg 표준 사용)')
    postproc.add_option(
        '--fixup',
        metavar='POLICY', dest='fixup', default='detect_or_warn',
        help='파일의 알려진 결함을 자동으로 수정합니다. '
             '절대(아무것도 하지 않음), 경고(경고만 발함),'
             'filename_or_filename(기본값; 가능하면 파일 수정, 그렇지 않으면 경고)')
    postproc.add_option(
        '--prefer-avconv',
        action='store_false', dest='prefer_ffmpeg',
        help='포스트 프로세서 실행을 위해 ffmpeg보다 avconv 선호')
    postproc.add_option(
        '--prefer-ffmpeg',
        action='store_true', dest='prefer_ffmpeg',
        help='포스트 프로세서 실행을 위해 avconv보다 ffmpeg 선호(기본값)')
    postproc.add_option(
        '--ffmpeg-location', '--avconv-location', metavar='PATH',
        dest='ffmpeg_location',
        help='fmpeg/avconv 바이너리의 위치로, 바이너리의 경로 또는 포함된 디렉토리 중 하나입니다.')
    postproc.add_option(
        '--exec',
        metavar='CMD', dest='exec_cmd',
        help='find\'s -exec 구문과 유사하게 다운로드 및 후 처리 후 파일에서 명령을 실행합니다. 예: --exec \'adb push {} /sdcard/Music/ &&rm {}\')')
    postproc.add_option(
        '--convert-subs', '--convert-subtitles',
        metavar='FORMAT', dest='convertsubtitles', default=None,
        help='자막을 다른 형식으로 변환합니다(현재 지원되는 형식: srt|ass|vtt|lrc).')

    # 여기까지 옵션 추가 
    parser.add_option_group(general)
    parser.add_option_group(network)
    parser.add_option_group(geo)
    parser.add_option_group(selection)
    parser.add_option_group(downloader)
    parser.add_option_group(filesystem)
    parser.add_option_group(thumbnail)
    parser.add_option_group(verbosity)
    parser.add_option_group(workarounds)
    parser.add_option_group(video_format)
    parser.add_option_group(subtitles)
    parser.add_option_group(authentication)
    parser.add_option_group(adobe_pass)
    parser.add_option_group(postproc)
    # 위의 옵션 추가그룹들을 parser에 저장
    if overrideArguments is not None: # 매개변수가 None이 아니면
        opts, args = parser.parse_args(overrideArguments) # 매개변수를 파싱함 (파싱 == 구문해석)
        if opts.verbose:
            write_string('[debug] Override config: ' + repr(overrideArguments) + '\n') # 큰 따옴표로 매개변수를 반환
    else: # None일때
        def compat_conf(conf):
            if sys.version_info < (3,): # 파이썬 버전이 2일때
                return [a.decode(preferredencoding(), 'replace') for a in conf]
            return conf

        command_line_conf = compat_conf(sys.argv[1:]) # 명령 인자값 반환
        opts, args = parser.parse_args(command_line_conf) # 명령 인자값을 해석(파싱)한 것을 반환받음

        system_conf = user_conf = custom_conf = []

        if '--config-location' in command_line_conf: # 명령을 받은 것이 구성파일 위치면
            location = compat_expanduser(opts.config_location) # 구성 파일 위치를 홈 디렉토리의 절대경로로 대체함
            if os.path.isdir(location): # 위치가 있을 경우
                location = os.path.join(location, 'youtube-dl.conf') # 구성파일 생성
            if not os.path.exists(location):
                parser.error('config-location %s does not exist.' % location) # 없으니 에러
            custom_conf = _readOptions(location) # 옵션을 읽고 디코딩된 location을 분할한 것을 모은 것을 반환
        elif '--ignore-config' in command_line_conf:
            pass
        else:
            system_conf = _readOptions('/etc/youtube-dl.conf') # 옵션을 읽고 디코딩된 /etc/youtube-dl.conf을 분할한 것을 모은 것을 반환
            if '--ignore-config' not in system_conf: 
                user_conf = _readUserConf() # user_conf를 만듦

        argv = system_conf + user_conf + custom_conf + command_line_conf
        opts, args = parser.parse_args(argv)
        if opts.verbose: # 상세 정보가 있을 경우?
            for conf_label, conf in (
                    ('System config', system_conf),
                    ('User config', user_conf),
                    ('Custom config', custom_conf),
                    ('Command-line args', command_line_conf)):
                write_string('[debug] %s: %s\n' % (conf_label, repr(_hide_login_info(conf)))) # 디버그 '~ config' : 로그인 옵션인지를 검색한 결과를 파일에 입력

    return parser, opts, args # 옵션들을 반환
