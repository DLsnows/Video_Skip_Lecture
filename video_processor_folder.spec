# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all data files for the frontend
datas = []

# Include frontend directory and all its contents recursively
frontend_path = 'frontend'
if os.path.exists(frontend_path):
    for root, dirs, files in os.walk(frontend_path):
        for file in files:
            file_path = os.path.join(root, file)
            dest_path = os.path.relpath(root, '.')
            datas.append((file_path, dest_path))

# Include config.json if it exists
if os.path.exists('config.json'):
    datas.append(('config.json', '.'))

# Include requirements files
if os.path.exists('requirements.txt'):
    datas.append(('requirements.txt', '.'))
if os.path.exists('requirements1.txt'):
    datas.append(('requirements1.txt', '.'))

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
    'whisperx.load_align_model',
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
    'whisperx.alignment.AlignModel',
    'whisperx.asr.FasterWhisperPipeline',
    'whisperx.audio.load_audio',
    'whisperx.transcribe.WhisperModel',
]

# Collect all modules from our application
hiddenimports += collect_submodules('api')
hiddenimports += collect_submodules('core')
hiddenimports += collect_submodules('utils')
hiddenimports += collect_submodules('config')

# Add encodings explicitly (often needed for PyInstaller)
hiddenimports += [
    'encodings',
    'encodings.cp1252',
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

# Create an EXE instance first
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for debugging purposes
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# Create a directory-based executable (COLLECT) that uses the EXE instance
coll = COLLECT(
    exe,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='VideoSkipLectureApp',
    debug=False,
    strip=False,
    upx=False,  # Disable UPX for directory-based distribution
    upx_exclude=[],
    warn_bootloader_missing_features=False,
    console=True,  # Keep console for debugging purposes
)