# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 스펙.

`--exclude-module` 은 파이썬 모듈만 거르고 Qt DLL 은 그대로 남는다.
이 앱은 QtWidgets/QtGui/QtCore 만 쓰는데 기본 수집에는 Qml, Quick, Pdf,
소프트웨어 OpenGL 폴백까지 딸려와 40MB 가까이 낭비된다. 그래서 수집이
끝난 뒤 바이너리 목록에서 직접 걸러낸다.

빌드 옵션은 환경변수로 받는다 (build.ps1 / build.sh 가 설정):
    DCCON_ONEFILE=1   단일 exe (Windows 전용)
    DCCON_CONSOLE=1   콘솔 창 표시 (디버깅용)

macOS 에서는 onedir 결과를 `.app` 번들로 한 번 더 싼다 (dist/디시콘 다운로더.app).
onefile `.app` 은 PyInstaller 가 더 이상 권장하지 않아 만들지 않는다.
"""

import os
import sys

MACOS = sys.platform == "darwin"

ONEFILE = os.environ.get("DCCON_ONEFILE") == "1" and not MACOS
CONSOLE = os.environ.get("DCCON_CONSOLE") == "1"

# 파이썬 모듈 단계에서 빼는 것들
EXCLUDED_MODULES = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQml",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DExtras",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DInput",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtBluetooth",
    "PySide6.QtPositioning", "PySide6.QtSerialPort", "PySide6.QtDesigner",
    "PySide6.QtTest", "PySide6.QtSql", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtSensors",
    "PySide6.QtSpatialAudio", "PySide6.QtTextToSpeech", "PySide6.QtWebSockets",
    "PySide6.QtWebChannel", "PySide6.QtNfc", "PySide6.QtHelp", "PySide6.QtUiTools",
    "tkinter", "unittest", "pydoc_data", "pdb", "doctest",
]

# 수집된 DLL 중 이름에 이게 들어가면 버린다.
#   opengl32sw : 소프트웨어 OpenGL 폴백 (20MB). QtWidgets 는 래스터 엔진을
#                쓰므로 필요 없다. 혹시 그래픽이 깨지는 환경이 나오면
#                이 항목만 빼고 다시 빌드하면 된다.
DROP_BINARIES = (
    "qt6quick", "qt6qml", "qt6pdf", "qt63d", "qt6charts", "qt6datavisualization",
    "qt6graphs", "qt6multimedia", "qt6bluetooth", "qt6positioning",
    "qt6serialport", "qt6designer", "qt6test", "qt6sql", "qt6remoteobjects",
    "qt6scxml", "qt6sensors", "qt6spatialaudio", "qt6texttospeech",
    "qt6websockets", "qt6webchannel", "qt6nfc", "qt6help", "qt6webengine",
    "qt6labs", "opengl32sw",
)
# macOS 는 Qt 가 `QtQuick.framework` 같은 프레임워크로 들어와 위 이름에 안 걸린다.
#   virtualkeyboard 입력 플러그인이 Quick/Qml 을, qpdf 이미지 플러그인이 QtPdf 를
#   끌고 오므로 플러그인째 뺀다. (imageformats 의 다른 플러그인은 건드리지 않는다.)
if MACOS:
    DROP_BINARIES += (
        "qt/lib/qtquick", "qt/lib/qtqml", "qt/lib/qtpdf", "qt/lib/qtvirtualkeyboard",
        "libqtvirtualkeyboardplugin", "imageformats/libqpdf",
    )

# 데이터 파일(플러그인 등) 중 버릴 경로 조각.
# imageformats 는 절대 건드리면 안 된다 - GIF/JPEG 썸네일이 안 그려진다.
DROP_DATA_DIRS = (
    "pyside6/qml", "pyside6/translations/qtwebengine",
    "pyside6/resources", "pyside6/plugins/qmltooling",
    "pyside6/plugins/sqldrivers", "pyside6/plugins/multimedia",
    "pyside6/plugins/position", "pyside6/plugins/sensors",
    "pyside6/plugins/texttospeech", "pyside6/plugins/designer",
)


def _keep_binary(entry):
    name = entry[0].replace("\\", "/").lower()
    # macOS 는 `QtQml -> PySide6/Qt/lib/QtQml.framework/...` 같은 SYMLINK 항목을
    # 따로 만든다. 이름만 봐서는 안 걸리므로 링크 대상도 본다.
    if entry[2] == "SYMLINK":
        name += " " + entry[1].replace("\\", "/").lower()
    return not any(token in name for token in DROP_BINARIES)


def _keep_data(entry):
    name = entry[0].replace("\\", "/").lower()
    if any(token in name for token in DROP_DATA_DIRS):
        return False
    # macOS 프레임워크의 심볼릭 링크와 Info.plist 는 데이터로 들어온다.
    # 바이너리만 빼면 끊어진 링크가 남으니 같은 규칙으로 걸러낸다.
    return not (MACOS and not _keep_binary(entry))


a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDED_MODULES,
    noarchive=False,
    optimize=0,
)

_before = len(a.binaries), len(a.datas)
a.binaries = [e for e in a.binaries if _keep_binary(e)]
a.datas = [e for e in a.datas if _keep_data(e)]
print(
    f"[spec] binaries {_before[0]} -> {len(a.binaries)}, "
    f"datas {_before[1]} -> {len(a.datas)}"
)

pyz = PYZ(a.pure)

_common = dict(
    name="dccon-downloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.icns" if MACOS else "assets/icon.ico",
)

if ONEFILE:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        exclude_binaries=False,
        runtime_tmpdir=None,
        **_common,
    )
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **_common)
    coll = COLLECT(
        exe, a.binaries, a.datas,
        strip=False, upx=False, name="dccon-downloader",
    )

if MACOS:
    import re

    # 스펙은 exec 로 돌아서 dccon 을 import 할 수 있다는 보장이 없다. 직접 읽는다.
    __version__ = re.search(
        r'__version__ = "([^"]+)"', open("dccon/__init__.py", encoding="utf-8").read()
    ).group(1)

    app = BUNDLE(
        coll,
        name="디시콘 다운로더.app",
        icon="assets/icon.icns",
        bundle_identifier="io.github.glglekdy.dccon-downloader",
        version=__version__,
        info_plist={
            "CFBundleDisplayName": "디시콘 다운로더",
            "CFBundleShortVersionString": __version__,
            "NSHighResolutionCapable": True,
            # 시스템 다크 모드를 따라가게 한다.
            "NSRequiresAquaSystemAppearance": False,
        },
    )
