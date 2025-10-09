#!/bin/bash

case "$(uname -s)" in
    Linux*)
        LIB_NAME="libdiscord_partner_sdk.so"
        ;;
    Darwin*)
        LIB_NAME="libdiscord_partner_sdk.dylib"
        ;;
    CYGWIN*|MINGW32*|MSYS*|MINGW*)
        LIB_NAME="discord_partner_sdk.dll"
        ;;
    *)
        echo "Unsupported platform: $(uname -s)"
        exit 1
        ;;
esac

echo "Detected platform: $(uname -s), using library: $LIB_NAME"

# trigger setuptools-scm
# FIXME: write a little script that writes to 
# anime_rpc/_version.py instead so we don't have 
# to do this every time
pip install -e .

# warning: --optimize 2 breaks cffi
# FIXME: only include relevant library for the platform
pyinstaller --onefile --name anime_rpc --optimize 1 --add-binary "./lib/$LIB_NAME:lib" --add-binary "./include/*:include" launcher.py
