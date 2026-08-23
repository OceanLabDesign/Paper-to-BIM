#!/bin/sh
# Paper-to-BIM 安裝程式（macOS：按兩下即可）
# 這支只負責找到 python3 然後把工作交給 install.py。
cd "$(dirname "$0")" || exit 1
for PY in python3.12 python3.13 python3.11 python3.10 python3; do
  if command -v "$PY" >/dev/null 2>&1; then
    echo "使用 $(command -v "$PY")"
    "$PY" install.py "$@"
    ST=$?
    echo
    echo "（按 Enter 關閉視窗）"; read -r _
    exit $ST
  fi
done
echo "找不到 Python 3。請先安裝："
echo "    brew install python@3.12 python-tk@3.12"
echo "或到 https://www.python.org/downloads/macos/ 下載官方版。"
echo; echo "（按 Enter 關閉視窗）"; read -r _
exit 1
