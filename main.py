#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaperIdea - 基于论文的 Idea 发现工具
程序入口

Copyright (c) 2024 antiproton
License: MIT
"""

import sys
from tkinter import Tk

from gui import PaperIdeaGUI


def main():
    """主函数"""
    print("=" * 60)
    print("📄 PaperIdea - 基于论文的 Idea 发现工具")
    print("=" * 60)
    print()
    
    # 创建主窗口
    root = Tk()
    
    # 设置 DPI 感知（Windows）
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    # 创建应用
    app = PaperIdeaGUI(root)
    
    # 运行主循环
    root.mainloop()


if __name__ == "__main__":
    main()
