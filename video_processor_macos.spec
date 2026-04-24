# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all data files for the frontend
datas = []

# Explicitly include frontend directory and all its contents
datas += [(os.path.join('frontend', '**', '*'), 'frontend')]

# Include config.json if it exists
if os.path.exists('config.json'):
    datas.append(('config.json', '.'))

# Include all submodules needed by the application
hiddenimports = [
    'fastapi',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'fastapi.staticfiles',
    'uvicorn',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.websockets',
    'uvicorn.server',
    'websockets',
    'websockets.server',
    'websockets.protocol',
    'transformers',
    'whisperx',
    'whisperx.audio',
    'whisperx.asr',
    'whisperx.alignment',
    'whisperx.diarize',
    'whisperx.utils',
    'whisperx.transcribe',
    'openai',
    'cv2',  # opencv-python
    'yt_dlp',
    'ffmpeg',
    'ffmpeg_python',  # Alternative name
    'pydantic',
    'pydantic.v1',
    'asyncio',
    'threading',
    'uuid',
    'webbrowser',
    'time',
    'pathlib',
    'typing',
    'os',
    'sys',
    'json',
    'traceback',
    'datetime',
    'multiprocessing',
    'concurrent.futures',
    'logging',
    'signal',
    'inspect',
    'click',
    'starlette',
    'starlette.requests',
    'starlette.responses',
    'starlette.types',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    'h11',
    'anyio',
    'anyio.lowlevel',
    'sniffio',
    'numpy',
    'torch',
    'torchaudio',
    'torchvision',
    'torch.nn',
    'torch.optim',
    'torch.utils',
    'torch.utils.data',
    'torch.backends',
    'speechbrain',
    'librosa',
    'soundfile',
    'scipy',
    'scipy.io',
    'scipy.signal',
    'sklearn',
    'sklearn.cluster',
    'sklearn.mixture',
    'alignment.algorithms',
]

# Collect all modules from our application
hiddenimports += collect_submodules('api')
hiddenimports += collect_submodules('core')
hiddenimports += collect_submodules('utils')
hiddenimports += collect_submodules('config')

# Add encodings explicitly (often needed for PyInstaller)
hiddenimports += [
    'encodings',
    'encodings.utf_8',
    'encodings.ascii',
]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],  # Include current directory in path
    binaries=[],
    datas=datas,  # Include frontend files and config
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VideoSkipLecture',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX is not compatible with macOS universal binaries
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Don't show console for macOS app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add path to an icns file if desired
)

# Create an app bundle for macOS
app = BUNDLE(
    exe,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VideoSkipLecture.app',
    debug=False,
    icon=None,  # Add path to an icns file if desired
    bundle_identifier='com.yourcompany.VideoSkipLecture',  # Change this to your bundle identifier
    info_plist={
        'CFBundleDisplayName': 'Video Skip Lecture',
        'CFBundleName': 'Video Skip Lecture',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSUIElement': False,  # Set to True if you don't want the app to appear in dock
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True,
        },
    }
)