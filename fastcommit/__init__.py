"""
FastCommit - AI 生成 Git Commit Message

一个使用 AI 大模型自动生成标准 Git Commit Message 的 Python 库
"""

__version__ = "0.0.2"
__author__ = "luzhixing12345"
__email__ = "luzhixing12345@163.com"

from .core import FastCommit
from .main import main

__all__ = ["FastCommit", "main"]
