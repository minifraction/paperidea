#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaperIdea 图形界面

Copyright (c) 2024 antiproton
License: MIT
"""

import os
import sys
import threading
from pathlib import Path
from tkinter import *
from tkinter import ttk, messagebox, filedialog

from api_client import DeepSeekClient, get_model_list, get_model_info
from config_manager import ConfigManager
from paper_analyzer import PaperAnalyzer
from utils import save_result, open_file


class PaperIdeaGUI:
    """PaperIdea 图形界面"""
    
    # 基础字体大小配置
    BASE_FONTS = {
        'title': 16,
        'subtitle': 12,
        'button': 11,
        'normal': 10,
        'small': 9,
        'nav_title': 14,
        'nav_subtitle': 9,
        'status': 9,
    }
    
    def __init__(self, root):
        self.root = root
        self.root.title("PaperIdea - 基于论文的 Idea 发现工具")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)
        
        # 配置管理
        self.config_manager = ConfigManager()
        config = self.config_manager.load_config()
        
        # 字体缩放比例
        self.font_scale = config.get('font_scale', 1.0)
        
        # 初始化客户端
        self.client = DeepSeekClient(
            api_key=config.get('api_key'),
            api_url=config.get('api_url'),
            model=config.get('model')
        )
        
        # 设置样式
        self.setup_styles()
        
        # 创建界面
        self.create_widgets()
        
        # 更新状态
        self.update_status()
    
    def get_font(self, font_type='normal'):
        """获取指定类型的字体大小
        
        Args:
            font_type: 字体类型，可选 title, subtitle, button, normal, small, nav_title, nav_subtitle, status
            
        Returns:
            字体元组 (字体名, 大小, [粗细])
        """
        base_size = self.BASE_FONTS.get(font_type, 10)
        actual_size = int(base_size * self.font_scale)
        
        if font_type in ['title', 'nav_title']:
            return ("微软雅黑", actual_size, "bold")
        elif font_type == 'subtitle':
            return ("微软雅黑", actual_size, "bold")
        elif font_type == 'button':
            return ("微软雅黑", actual_size, "bold")
        else:
            return ("微软雅黑", actual_size)
    
    def setup_styles(self):
        """设置样式"""
        self.style = ttk.Style()
        self.style.configure("Title.TLabel", font=self.get_font('title'))
        self.style.configure("Subtitle.TLabel", font=self.get_font('subtitle'))
        self.style.configure("Action.TButton", font=self.get_font('button'))
    
    def update_all_fonts(self):
        """更新所有字体"""
        # 更新 ttk 样式
        self.setup_styles()
        
        # 更新导航栏字体
        if hasattr(self, 'nav_title_label'):
            self.nav_title_label.config(font=self.get_font('nav_title'))
        if hasattr(self, 'nav_subtitle_label'):
            self.nav_subtitle_label.config(font=self.get_font('nav_subtitle'))
        
        # 更新版本标签
        if hasattr(self, 'version_label'):
            self.version_label.config(font=self.get_font('small'))
        
        # 更新彩色按钮字体
        for btn in getattr(self, 'nav_buttons', []):
            btn.config(font=self.get_font('button'))
        
        # 更新结果文本框字体
        if hasattr(self, 'result_text'):
            self.result_text.config(font=self.get_font('normal'))
        
        # 更新提供商标签字体
        if hasattr(self, 'provider_label'):
            self.provider_label.config(font=self.get_font('small'))
        
        # 强制刷新界面
        self.root.update_idletasks()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 标题栏
        self.create_header()
        
        # 左侧导航
        self.create_nav_panel()
        
        # 底部状态栏（必须在 create_content_area 之前创建，因为后者会调用 update_status）
        self.create_status_bar()
        
        # 右侧内容区
        self.create_content_area()
    
    def create_header(self):
        """创建标题栏"""
        header = ttk.Frame(self.main_frame)
        header.pack(fill=X, pady=(0, 10))
        
        title = ttk.Label(header, text="📄 PaperIdea - 基于论文的 Idea 发现工具", 
                         style="Title.TLabel")
        title.pack(side=LEFT)
        
        subtitle = ttk.Label(header, text="输入论文，发现延伸研究方向", 
                            font=self.get_font('normal'), foreground="gray")
        subtitle.pack(side=LEFT, padx=(10, 0))
    
    def create_nav_panel(self):
        """创建左侧导航面板"""
        # 使用 Frame 自定义彩色背景
        nav_frame = Frame(self.main_frame, width=200, bg="#2C3E50")
        nav_frame.pack(side=LEFT, fill=Y, padx=(0, 10))
        nav_frame.pack_propagate(False)
        
        # 标题
        self.nav_title_label = Label(nav_frame, text="🚀 功能导航", 
                           font=self.get_font('nav_title'),
                           bg="#2C3E50", fg="#ECF0F1")
        self.nav_title_label.pack(pady=(15, 10), padx=10)
        
        # 副标题
        self.nav_subtitle_label = Label(nav_frame, text="选择功能开始探索", 
                        font=self.get_font('nav_subtitle'),
                        bg="#2C3E50", fg="#BDC3C7")
        self.nav_subtitle_label.pack(pady=(0, 15), padx=10)
        
        # 存储导航按钮列表
        self.nav_buttons = []
        
        # API 配置按钮（橙色）
        btn = self.create_color_button(nav_frame, "🔑 API 配置", "#E67E22", "#D35400",
                                lambda: self.show_frame("config"))
        self.nav_buttons.append(btn)
        
        # 分隔线
        Frame(nav_frame, height=2, bg="#34495E").pack(fill=X, padx=15, pady=12)
        
        # 核心功能按钮（蓝色）
        btn = self.create_color_button(nav_frame, "📄 论文分析", "#3498DB", "#2980B9",
                                lambda: self.show_frame("analyze"))
        self.nav_buttons.append(btn)
        
        # 分隔线
        Frame(nav_frame, height=2, bg="#34495E").pack(fill=X, padx=15, pady=12)
        
        # 辅助功能按钮（灰色）
        btn = self.create_color_button(nav_frame, "📂 打开输出目录", "#7F8C8D", "#616A6B",
                                self.open_outputs_dir)
        self.nav_buttons.append(btn)
        
        btn = self.create_color_button(nav_frame, "❓ 使用帮助", "#7F8C8D", "#616A6B",
                                self.show_help)
        self.nav_buttons.append(btn)
        
        # 底部信息
        self.version_label = Label(nav_frame, text="v1.0", 
                             font=self.get_font('small'),
                             bg="#2C3E50", fg="#95A5A6")
        self.version_label.pack(side=BOTTOM, pady=10)
    
    def create_color_button(self, parent, text, bg_color, hover_color, command):
        """创建彩色按钮"""
        btn = Button(parent, text=text,
                    font=self.get_font('button'),
                    bg=bg_color, fg="white",
                    activebackground=hover_color, activeforeground="white",
                    relief=FLAT, cursor="hand2",
                    command=command,
                    width=18, height=1)
        btn.pack(pady=5, padx=10, ipady=5)
        
        # 添加悬停效果
        def on_enter(e):
            btn.config(bg=hover_color)
        def on_leave(e):
            btn.config(bg=bg_color)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def create_content_area(self):
        """创建右侧内容区域"""
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(side=LEFT, fill=BOTH, expand=True)
        
        # 创建各个页面
        self.frames = {}
        self.create_config_frame()
        self.create_analyze_frame()
        
        # 默认显示分析页面
        self.show_frame("analyze")
    
    def create_config_frame(self):
        """创建 API 配置页面"""
        frame = ttk.Frame(self.content_frame)
        self.frames["config"] = frame
        
        # 标题
        ttk.Label(frame, text="🔑 DeepSeek API 配置", 
                 style="Subtitle.TLabel").pack(anchor=W, pady=(0, 20))
        
        # 说明
        info_text = """请选择模型厂商并配置对应的 API Key。

支持: DeepSeek | 豆包 | Kimi | GLM | MiniMax

1. 选择下方列表中的模型
2. 根据厂商提示获取 API Key
3. 将 API Key 粘贴到下方并保存"""
        
        info = ttk.Label(frame, text=info_text, wraplength=600, justify=LEFT,
                        font=self.get_font('normal'))
        info.pack(anchor=W, pady=(0, 20))
        
        # API Key 输入
        ttk.Label(frame, text="API Key:").pack(anchor=W)
        
        # 获取当前配置
        current_key = self.client.api_key if self.client.api_key else ""
        self.api_key_var = StringVar(value=current_key)
        
        key_frame = ttk.Frame(frame)
        key_frame.pack(fill=X, pady=(5, 20))
        
        self.api_key_entry = ttk.Entry(key_frame, textvariable=self.api_key_var, 
                                       show="*", width=60)
        self.api_key_entry.pack(side=LEFT, fill=X, expand=True)
        
        self.show_key_var = BooleanVar(value=False)
        ttk.Checkbutton(key_frame, text="显示", variable=self.show_key_var,
                       command=self.toggle_key_visibility).pack(side=LEFT, padx=(10, 0))
        
        # 模型选择
        ttk.Label(frame, text="模型:").pack(anchor=W)
        self.model_var = StringVar(value=self.client.model)
        
        # 获取所有支持的模型
        all_models = get_model_list()
        
        # 创建带分组的模型选择
        model_combo = ttk.Combobox(frame, textvariable=self.model_var, 
                                   values=all_models,
                                   state="readonly", width=30)
        model_combo.pack(anchor=W, pady=(5, 5))
        
        # 显示当前模型的厂商信息
        self.provider_label = ttk.Label(frame, text="", foreground="gray", font=self.get_font('small'))
        self.provider_label.pack(anchor=W, pady=(0, 10))
        
        # 更新厂商显示
        def update_provider_label(*args):
            model = self.model_var.get()
            info = get_model_info(model)
            self.provider_label.config(text=f"厂商: {info['provider']} | API: {info['api_url']}")
        
        self.model_var.trace_add("write", update_provider_label)
        update_provider_label()  # 初始化显示
        
        # 注：如需自定义顶刊列表，请编辑 prompts/top_journals.txt
        
        # 按钮框架
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(anchor=W, pady=(10, 0))
        
        # 保存按钮
        btn_save = ttk.Button(btn_frame, text="💾 保存配置", 
                              command=self.save_config,
                              style="Action.TButton")
        btn_save.pack(side=LEFT, padx=(0, 10))
        
        # 测试连接按钮
        btn_test = ttk.Button(btn_frame, text="🔗 测试连接", 
                              command=self.test_connection,
                              style="Action.TButton")
        btn_test.pack(side=LEFT)
        
        # 分隔线
        ttk.Separator(frame, orient=HORIZONTAL).pack(fill=X, pady=(30, 20))
        
        # 字体大小设置
        ttk.Label(frame, text="📝 界面字体设置", 
                 style="Subtitle.TLabel").pack(anchor=W, pady=(0, 10))
        
        font_info = ttk.Label(frame, text="调整界面字体大小，实时生效", 
                             font=self.get_font('small'), foreground="gray")
        font_info.pack(anchor=W, pady=(0, 15))
        
        # 字体大小滑块
        font_frame = ttk.Frame(frame)
        font_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(font_frame, text="小", font=self.get_font('small')).pack(side=LEFT)
        
        self.font_scale_var = DoubleVar(value=self.font_scale)
        font_slider = ttk.Scale(font_frame, from_=0.8, to=1.5, orient=HORIZONTAL,
                               variable=self.font_scale_var, length=300)
        font_slider.pack(side=LEFT, padx=10, fill=X, expand=True)
        
        ttk.Label(font_frame, text="大", font=self.get_font('small')).pack(side=LEFT)
        
        # 字体大小显示
        self.font_size_label = ttk.Label(frame, text=f"当前缩放: {self.font_scale:.1f}x", 
                                        font=self.get_font('normal'))
        self.font_size_label.pack(anchor=W, pady=(5, 15))
        
        # 实时更新字体预览
        def on_font_scale_changed(*args):
            scale = self.font_scale_var.get()
            self.font_scale = round(scale, 1)
            self.font_size_label.config(text=f"当前缩放: {self.font_scale:.1f}x")
        
        self.font_scale_var.trace_add("write", on_font_scale_changed)
        
        # 应用按钮
        btn_font = ttk.Button(frame, text="✨ 应用字体设置", 
                             command=self.apply_font_scale,
                             style="Action.TButton")
        btn_font.pack(anchor=W, pady=(0, 10))
        
        # 提示
        font_tip = ttk.Label(frame, text="提示：字体设置会自动保存，下次启动时生效", 
                            font=self.get_font('small'), foreground="gray")
        font_tip.pack(anchor=W)
    
    def create_analyze_frame(self):
        """创建论文分析页面"""
        frame = ttk.Frame(self.content_frame)
        self.frames["analyze"] = frame
        
        # 标题
        ttk.Label(frame, text="📄 基于论文的 Idea 发现", 
                 style="Subtitle.TLabel").pack(anchor=W, pady=(0, 10))
        
        # 说明
        info = """输入一篇论文（PDF 文件或 arXiv 链接），AI 将：
1. 解析论文：提取问题、模型、算法、贡献、局限性、未来工作
2. 精准调研：基于论文关键信息搜索相关工作
3. 方法迁移搜索：查找"同模型相似方法"和"相似方法不同模型"的组合（最容易出论文！）
4. 生成 Idea：从该论文出发，提出具体的延伸研究方向

⭐ 特别关注：
  • Type B1: 同模型相似方法（控制变量，对比实验）
  • Type B2: 相似方法不同模型（方法迁移，填补空白）
  这两类工作最容易发表！

⚠️ Type A（直接改进）最难：容易改进的话原作者大概率已经做了"""
        
        ttk.Label(frame, text=info, wraplength=600, justify=LEFT,
                 font=self.get_font('normal')).pack(anchor=W, pady=(0, 20))
        
        # 输入框
        ttk.Label(frame, text="论文输入:", font=self.get_font('normal')).pack(anchor=W)
        
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=X, pady=(5, 5))
        
        self.paper_input_var = StringVar()
        self.paper_input_entry = ttk.Entry(input_frame, textvariable=self.paper_input_var, width=60)
        self.paper_input_entry.pack(side=LEFT, fill=X, expand=True)
        
        # 文件选择按钮
        btn_browse = ttk.Button(input_frame, text="📂 选择 PDF", 
                               command=self.browse_pdf_file)
        btn_browse.pack(side=LEFT, padx=(10, 0))
        
        # 示例
        examples = [
            "arxiv:2403.08774",
            "https://arxiv.org/abs/2401.12345", 
            "./papers/paper.pdf"
        ]
        
        ttk.Label(frame, text="示例:", font=self.get_font('normal')).pack(anchor=W, pady=(10, 0))
        for ex in examples:
            ttk.Button(frame, text=ex, command=lambda e=ex: self.paper_input_var.set(e)).pack(
                anchor=W, pady=2)
        
        # 运行按钮
        btn_run = ttk.Button(frame, text="▶️ 开始分析论文", 
                            command=self.run_analysis,
                            style="Action.TButton")
        btn_run.pack(anchor=W, pady=(20, 10))
        
        # 进度条
        self.progress = ttk.Progressbar(frame, mode='indeterminate', length=400)
        self.progress.pack(anchor=W, pady=(10, 10))
        self.progress.pack_forget()  # 默认隐藏
        
        # 状态标签
        self.status_label = ttk.Label(frame, text="", foreground="blue",
                                     font=self.get_font('normal'))
        self.status_label.pack(anchor=W)
        
        # 调试信息区域：显示arXiv搜索关键词
        debug_frame = ttk.LabelFrame(frame, text="调试信息：arXiv搜索关键词", padding=5)
        debug_frame.pack(fill=X, pady=(10, 5))
        
        # 搜索词文本框
        from tkinter import scrolledtext
        self.debug_text = scrolledtext.ScrolledText(debug_frame, wrap=WORD, height=4,
                                                     font=self.get_font('small'))
        self.debug_text.pack(fill=X, expand=True)
        self.debug_text.insert(1.0, "点击'开始分析论文'后，这里将显示用于arXiv搜索的关键词...")
        self.debug_text.config(state=DISABLED)
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(frame, text="分析结果预览", padding=10)
        result_frame.pack(fill=BOTH, expand=True, pady=(10, 0))
        
        # 滚动文本框
        self.result_text = scrolledtext.ScrolledText(result_frame, wrap=WORD, height=15,
                                                     font=self.get_font('normal'))
        self.result_text.pack(fill=BOTH, expand=True)
        self.result_text.insert(1.0, "分析结果将显示在这里...")
        self.result_text.config(state=DISABLED)
    
    def create_status_bar(self):
        """创建底部状态栏"""
        self.status_bar = ttk.Frame(self.root, relief=SUNKEN, padding=(5, 2))
        self.status_bar.pack(side=BOTTOM, fill=X)
        
        self.status_text = ttk.Label(self.status_bar, text="就绪", font=self.get_font('status'))
        self.status_text.pack(side=LEFT)
        
        self.api_status = ttk.Label(self.status_bar, text="API: 未配置", 
                                   foreground="red", font=self.get_font('status'))
        self.api_status.pack(side=RIGHT)
    
    def show_frame(self, frame_name):
        """切换页面"""
        for name, frame in self.frames.items():
            frame.pack_forget()
        
        self.frames[frame_name].pack(fill=BOTH, expand=True)
        self.update_status()
    
    def update_status(self):
        """更新状态栏"""
        if self.client.is_configured():
            provider = getattr(self.client, 'provider', 'AI')
            self.api_status.config(text=f"API: {provider} 已配置 ✓", foreground="green")
        else:
            self.api_status.config(text="API: 未配置 ✗", foreground="red")
    
    def toggle_key_visibility(self):
        """切换 API Key 显示/隐藏"""
        if self.show_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")
    
    def save_config(self):
        """保存配置"""
        api_key = self.api_key_var.get().strip()
        model = self.model_var.get()
        
        if not api_key:
            messagebox.showerror("错误", "API Key 不能为空")
            return
        
        try:
            # 获取模型对应的 API URL
            info = get_model_info(model)
            api_url = info.get("api_url", "")
            
            self.config_manager.save_config(api_key=api_key, model=model, api_url=api_url, 
                                           font_scale=self.font_scale, domain='unspecified')
            
            # 更新客户端
            self.client.api_key = api_key
            self.client.model = model
            self.client.api_url = api_url
            self.client.provider = info.get("provider", "未知")
            
            self.update_status()
            messagebox.showinfo("成功", f"配置已保存！\n厂商: {info['provider']}\n模型: {model}")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def apply_font_scale(self):
        """应用字体大小设置"""
        try:
            # 保存到配置
            config = self.config_manager.load_config()
            self.config_manager.save_config(
                api_key=config.get('api_key', ''),
                api_url=config.get('api_url', ''),
                model=config.get('model', 'deepseek-chat'),
                font_scale=self.font_scale,
                domain=config.get('domain', 'unspecified')
            )
            
            # 应用字体更新
            self.update_all_fonts()
            
            messagebox.showinfo("成功", f"字体大小已调整为 {self.font_scale:.1f}x\n界面已更新！")
        except Exception as e:
            messagebox.showerror("错误", f"应用字体设置失败: {str(e)}")
    
    def test_connection(self):
        """测试 API 连接"""
        if not self.client.is_configured():
            messagebox.showerror("错误", "请先配置 API Key")
            return
        
        self.status_text.config(text="正在测试连接...")
        self.root.update()
        
        try:
            success, msg = self.client.test_connection()
            if success:
                messagebox.showinfo("成功", "连接成功！API 工作正常。")
            else:
                messagebox.showerror("错误", f"连接失败: {msg}")
        except Exception as e:
            messagebox.showerror("错误", f"连接失败: {str(e)}")
        finally:
            self.status_text.config(text="就绪")
    
    def browse_pdf_file(self):
        """浏览选择 PDF 文件"""
        filepath = filedialog.askopenfilename(
            title="选择论文 PDF 文件",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filepath:
            self.paper_input_var.set(filepath)
    
    def run_analysis(self):
        """运行论文分析"""
        paper_input = self.paper_input_var.get().strip()
        if not paper_input:
            messagebox.showerror("错误", "请输入论文 arXiv ID 或选择 PDF 文件")
            return
        
        if not self.client.is_configured():
            messagebox.showerror("错误", "请先配置 API Key")
            self.show_frame("config")
            return
        
        # 显示进度条
        self.progress.pack(anchor=W, pady=(10, 10))
        self.progress.start()
        self.status_label.config(text="Step 1/6: 提取论文文本...")
        self.status_text.config(text="正在分析论文...")
        
        # 清空结果区
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)
        self.result_text.insert(1.0, "正在分析中，请稍候...")
        self.result_text.config(state=DISABLED)
        
        def update_status(msg):
            """更新状态显示"""
            self.root.after(0, lambda: self.status_label.config(text=msg))
            self.root.after(0, lambda: self.status_text.config(text=msg))
        
        def update_result(text):
            """更新结果显示"""
            self.root.after(0, lambda: self._set_result_text(text))
        
        def task():
            try:
                # 创建分析器
                analyzer = PaperAnalyzer(self.client)
                
                # 执行分析
                report, paper_title, search_info = analyzer.analyze(paper_input, status_callback=update_status)
                
                # 更新调试信息显示搜索关键词
                def update_debug_info():
                    self.debug_text.config(state=NORMAL)
                    self.debug_text.delete(1.0, END)
                    
                    search_terms = search_info.get("search_terms", [])
                    model_expansion = search_info.get("model_expansion", {})
                    
                    debug_text = "【用于arXiv搜索的关键词】\n"
                    if search_terms:
                        debug_text += f"搜索词 ({len(search_terms)}个): {', '.join(search_terms)}\n"
                    else:
                        debug_text += "搜索词: 未提取到模型名称\n"
                    
                    # 显示语义扩展详情
                    original = model_expansion.get("original", [])
                    similar = model_expansion.get("similar_models", [])
                    broader = model_expansion.get("broader_concepts", [])
                    
                    if original:
                        debug_text += f"\n原始模型: {', '.join(original)}\n"
                    if similar:
                        debug_text += f"相似模型: {', '.join(similar)}\n"
                    if broader:
                        debug_text += f"更广概念: {', '.join(broader)}\n"
                    
                    self.debug_text.insert(1.0, debug_text)
                    self.debug_text.config(state=DISABLED)
                
                self.root.after(0, update_debug_info)
                
                # 保存结果
                update_status("Step 5/6: 保存报告...")
                safe_title = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in paper_title[:30])
                filepath = save_result("paper-discovery", safe_title, report)
                
                # 打开文件
                try:
                    open_file(filepath)
                except:
                    pass
                
                # 更新结果显示
                update_result(report[:2000] + "\n\n... [报告已保存并打开] ...")
                
                update_status("Step 6/6: 完成！")
                self.root.after(0, lambda: self.status_label.config(
                    text=f"✓ 完成！报告已保存: {filepath.name}"))
                
            except Exception as e:
                update_status(f"❌ 错误: {str(e)}")
                update_result(f"错误: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
            finally:
                self.root.after(0, self.progress.stop)
                self.root.after(0, self.progress.pack_forget)
                self.root.after(0, lambda: self.status_text.config(text="就绪"))
        
        threading.Thread(target=task, daemon=True).start()
    
    def _set_result_text(self, text):
        """设置结果文本"""
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)
        self.result_text.insert(1.0, text)
        self.result_text.config(state=DISABLED)
    
    def open_outputs_dir(self):
        """打开输出目录"""
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        try:
            open_file(output_dir)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开目录: {e}")
    
    def show_help(self):
        """显示帮助"""
        help_text = """PaperIdea 使用帮助

1. 配置 API Key
   - 点击左侧"🔑 API 配置"
   - 选择模型厂商（DeepSeek/豆包/Kimi/GLM/MiniMax）
   - 选择研究领域（unspecified为通用）
   - 输入对应厂商的 API Key
   - 点击"保存配置"

2. 获取各厂商 API Key
   • DeepSeek: https://platform.deepseek.com/
   • 豆包: https://console.volcengine.com/ark
   • Kimi: https://platform.moonshot.cn/
   • GLM: https://open.bigmodel.cn/
   • MiniMax: https://platform.minimaxi.com/

3. 分析论文
   - 点击左侧"📄 论文分析"
   - 输入 arXiv ID 或选择 PDF 文件
   - 点击"开始分析论文"
   - 等待分析完成

4. 查看结果
   - 分析完成后自动打开报告
   - 报告保存在 outputs/ 目录

支持的输入格式:
- arXiv ID: arxiv:2401.12345
- arXiv 链接: https://arxiv.org/abs/2401.12345
- PDF 文件: ./papers/my_paper.pdf

问题反馈:
如有问题，请检查 API Key 是否正确配置。"""
        
        messagebox.showinfo("使用帮助", help_text)


def main():
    """主函数"""
    root = Tk()
    app = PaperIdeaGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
