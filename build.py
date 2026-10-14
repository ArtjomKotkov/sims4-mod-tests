"""Собирает dist/EasyCheats.ts4script.

The Sims 4 загружает только байткод Python 3.7, поэтому скрипт нужно запускать
интерпретатором Python 3.7:  py -3.7 build.py   (Windows)  /  python3.7 build.py
"""
import compileall
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
BUILD = os.path.join(ROOT, 'build')
DIST = os.path.join(ROOT, 'dist')
NAME = 'EasyCheats.ts4script'


def main():
    if sys.version_info[:2] != (3, 7):
        sys.exit('Нужен Python 3.7 (сейчас {}.{}).'.format(*sys.version_info[:2]))
    shutil.rmtree(BUILD, ignore_errors=True)
    shutil.copytree(SRC, BUILD, ignore=shutil.ignore_patterns('__pycache__'))
    if not compileall.compile_dir(BUILD, quiet=1, legacy=True):
        sys.exit('Ошибка компиляции.')
    os.makedirs(DIST, exist_ok=True)
    target = os.path.join(DIST, NAME)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_STORED) as archive:
        for folder, _, files in os.walk(BUILD):
            for file_name in sorted(files):
                if file_name.endswith('.pyc'):
                    path = os.path.join(folder, file_name)
                    archive.write(path, os.path.relpath(path, BUILD))
    shutil.rmtree(BUILD)
    print('Готово:', target)


if __name__ == '__main__':
    main()
