#!/bin/bash

# trigger setuptools-scm
# FIXME: write a little script that writes to 
# anime_rpc/_version.py instead so we don't have 
# to do this every time
pip install -e .

# warning: --optimize 2 breaks cffi
# FIXME: only include relevant library for the platform
pyinstaller --onefile --name anime_rpc --optimize 1 --add-binary "./lib/*:lib" --add-binary "./include/*:include" launcher.py
