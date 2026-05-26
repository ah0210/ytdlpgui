import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import subprocess
import queue
import os
import sys
import threading
import tempfile
from ttkthemes import ThemedTk
import ctypes
import webbrowser
import configparser
import shutil
import json
from datetime import datetime

def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容 PyInstaller 打包"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 设置DPI感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

class YtDlpGUI:
    def __init__(self, master):
        self.master = master
        master.title("yt-dlp GUI")
        
        # 设置主题
        self.style = ttk.Style()
        self.style.theme_use('equilux')  # 使用equilux主题作为基础
        
        # 配置主题颜色
        self.style.configure('TFrame', background='#464646')
        self.style.configure('TLabel', background='#464646', foreground='white', font=('Segoe UI', 10))
        self.style.configure('TButton', background='#2b2b2b', foreground='white', font=('Segoe UI', 10))
        self.style.configure('TCheckbutton', background='#464646', foreground='white', font=('Segoe UI', 10))
        self.style.configure('TEntry', fieldbackground='#2b2b2b', foreground='white', font=('Segoe UI', 10))
        self.style.configure('TCombobox', fieldbackground='#2b2b2b', foreground='white', background='#2b2b2b', font=('Segoe UI', 10))
        self.style.map('TCombobox',
            fieldbackground=[('readonly', '#2b2b2b'), ('disabled', '#2b2b2b')],
            foreground=[('readonly', 'white'), ('disabled', '#666666')],
            selectbackground=[('readonly', '#404040')],
            selectforeground=[('readonly', 'white')])
        
        # 配置按钮样式
        self.style.map('TButton',
            background=[('active', '#404040'), ('disabled', '#2b2b2b')],
            foreground=[('disabled', '#666666')])
        
        # 状态栏按钮样式 - 小巧一点
        self.style.configure('Status.TButton', font=('Segoe UI', 9), padding=(4, 0))
        
        # 状态栏按钮样式 - 小巧一点
        self.style.configure('Status.TButton', font=('Segoe UI', 9), padding=(4, 0))
        
        # 配置复选框样式
        self.style.map('TCheckbutton',
            background=[('active', '#404040')],
            foreground=[('disabled', '#666666')])
        
        # 配置输入框样式
        self.style.map('TEntry',
            fieldbackground=[('disabled', '#2b2b2b')],
            foreground=[('disabled', '#666666')])

        # 创建主框架
        self.main_frame = ttk.Frame(master, padding="10")
        self.main_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 读取配置文件
        self.config = configparser.ConfigParser()
        try:
            self.config.read('settings.ini')
            self.download_path = self.config.get('Settings', 'download_path')
            self.ytdlp_path = self.config.get('Settings', 'ytdlp_path')
        except:
            # 如果配置文件不存在或读取失败，使用默认值
            self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
            self.ytdlp_path = "yt-dlp"
            if not os.path.exists(self.download_path):
                self.download_path = os.getcwd()

        self.last_downloaded_file = None

        # URL输入区域
        self.url_label = ttk.Label(self.main_frame, text="URL:")
        self.url_label.grid(row=0, column=0, padx=12, pady=(12, 6), sticky=tk.W)
        
        # URL输入框和清除按钮的容器
        self.url_frame = ttk.Frame(self.main_frame)
        self.url_frame.grid(row=0, column=1, padx=12, pady=(12, 6), sticky=tk.W + tk.E)
        
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(self.url_frame, width=60, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)  # Use ipady to match other entries and fill X only
        # self.url_var.trace_add("write", self.on_url_change) # 移除自动去除参数功能
        self.url_entry.bind('<Return>', lambda e: self.start_download())  # Enter 键触发下载
        
        self.clean_button = ttk.Button(self.url_frame, text="清除参数", width=10, command=self.clean_url_params)
        self.clean_button.pack(side=tk.LEFT, padx=(4, 0))

        self.clear_button = ttk.Button(self.url_frame, text="清空", width=5, command=self.clear_url)
        self.clear_button.pack(side=tk.LEFT, padx=(4, 0))
        
        self.url_frame.grid_columnconfigure(0, weight=1)
        
        # 各选项详细配置区域
        self.detail_area = ttk.Frame(self.main_frame)
        self.detail_area.grid(row=2, column=0, columnspan=2, padx=12, pady=(0, 6), sticky=(tk.W, tk.E))

        # 重命名详细配置
        self.rename_detail = ttk.Frame(self.detail_area)
        ttk.Label(self.rename_detail, text="重命名文件名:").pack(side=tk.LEFT, padx=(0, 4))
        self.rename_entry = ttk.Entry(self.rename_detail, width=25)
        self.rename_entry.pack(side=tk.LEFT, ipady=2)
        ttk.Label(self.rename_detail, text="标签:").pack(side=tk.LEFT, padx=(8, 4))
        self.tag_entry = ttk.Combobox(self.rename_detail, width=15)
        self.tag_entry.pack(side=tk.LEFT, ipady=2)
        ttk.Button(self.rename_detail, text="×", width=1, command=self.clear_all_tags).pack(side=tk.LEFT, padx=2)

        # Cookie详细配置
        self.cookie_detail = ttk.Frame(self.detail_area)
        self.cookie_files = []
        ttk.Label(self.cookie_detail, text="Cookie文件:").pack(side=tk.LEFT, padx=(0, 4))
        self.cookie_combo = ttk.Combobox(self.cookie_detail, width=20, state='readonly')
        self.cookie_combo.pack(side=tk.LEFT, ipady=2)
        self.cookie_combo.bind("<<ComboboxSelected>>", self.on_cookie_select)
        ttk.Button(self.cookie_detail, text="添加", width=5, command=self.add_cookie_file).pack(side=tk.LEFT, padx=(4, 2))
        ttk.Button(self.cookie_detail, text="刷新", width=5, command=self.reload_cookie_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.cookie_detail, text="编辑", width=5, command=self.open_cookie_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.cookie_detail, text="删除", width=5, command=self.delete_cookie_file).pack(side=tk.LEFT, padx=2)
        self.reload_cookie_files()

        # 代理详细配置
        self.proxy_detail = ttk.Frame(self.detail_area)
        ttk.Label(self.proxy_detail, text="代理地址:").pack(side=tk.LEFT, padx=(0, 4))
        self.proxy_entry = ttk.Entry(self.proxy_detail, width=30)
        self.proxy_entry.pack(side=tk.LEFT, ipady=2)
        ttk.Button(self.proxy_detail, text="7890", width=5, command=lambda: self.proxy_entry.delete(0, tk.END) or self.proxy_entry.insert(0, "127.0.0.1:7890")).pack(side=tk.LEFT, padx=4)

        # 初始隐藏所有详细配置
        self.rename_detail.grid_forget()
        self.cookie_detail.grid_forget()
        self.proxy_detail.grid_forget()
        
        # 日志框（始终显示）
        self.log_frame = ttk.Frame(self.main_frame)
        self.log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=12, pady=(0, 12))
        self.log_text = tk.Text(self.log_frame, bg='#2b2b2b', fg='white', insertbackground='white',
                               font=('Consolas', 10), relief=tk.FLAT, borderwidth=0,
                               highlightthickness=0, padx=5, pady=5,
                               yscrollcommand=lambda f, l: None)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 历史记录区域（默认隐藏）
        self.history_frame = ttk.Frame(self.main_frame)
        self.history_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=12, pady=(0, 12))
        self.history_frame.grid_forget()
        
        # 内部标题和清空按钮区域
        self.history_inner_header = ttk.Frame(self.history_frame)
        self.history_inner_header.pack(fill=tk.X, padx=2, pady=2)
        
        self.history_label = ttk.Label(self.history_inner_header, text="历史记录:", font=('Segoe UI', 9, 'bold'))
        self.history_label.pack(side=tk.LEFT, padx=5)
        
        self.clear_history_button = tk.Button(self.history_inner_header, 
                                            text="清空记录", 
                                            command=self.clear_history,
                                            font=('Segoe UI', 8),
                                            fg='#888888',
                                            bg='#2b2b2b',
                                            activebackground='#404040',
                                            activeforeground='white',
                                            relief=tk.FLAT,
                                            padx=8)
        self.clear_history_button.pack(side=tk.RIGHT, padx=5)
        
        # 列表框 - 使用灰色边框，去除亮白色
        self.history_listbox = tk.Listbox(self.history_frame, 
                                          bg='#2b2b2b', 
                                          fg='#cccccc',
                                          selectbackground='#404040', 
                                          font=('Segoe UI', 9),
                                          borderwidth=0,
                                          highlightthickness=1,
                                          highlightbackground='#555555',  # 深灰色边框
                                          highlightcolor='#777777')       # 选中时的边框
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.history_listbox.bind('<Double-Button-1>', self.on_history_select)
        
        history_scrollbar = ttk.Scrollbar(self.history_frame, orient=tk.VERTICAL, command=self.history_listbox.yview)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox.config(yscrollcommand=history_scrollbar.set)
        
        # 历史记录文件路径
        self.history_file = 'download_history.json'
        self.load_history()
        
        # 加载 Tags
        self.tags_data = []
        self.load_tags()

        # 配置网格权重
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(1, weight=1)  # 主框架可扩展
        master.grid_rowconfigure(0, minsize=30)  # 标题栏高度
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(4, weight=1)  # 内容区域可扩展
        
        # 自定义标题栏（可拖拽）
        self.title_bar = tk.Frame(master, bg='#333333', height=30)
        self.title_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.title_bar.bind('<Button-1>', self.start_drag)
        self.title_bar.bind('<B1-Motion>', self.on_drag)
        
        self.title_label = tk.Label(self.title_bar, text="ytdlpGUI", bg='#333333', fg='#aaaaaa', font=('Segoe UI', 10))
        self.title_label.pack(side=tk.LEFT, padx=10)
        
        for child in [self.title_label]:
            child.bind('<Button-1>', self.start_drag)
            child.bind('<B1-Motion>', self.on_drag)
        
        # 选项开关
        self.rename_var = tk.BooleanVar()
        tk.Checkbutton(self.title_bar, text="重命名", variable=self.rename_var, command=self.on_rename_toggle,
                      bg='#333333', fg='#aaaaaa', selectcolor='#404040', activebackground='#404040',
                      font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=6)
        
        self.cookie_var = tk.BooleanVar()
        tk.Checkbutton(self.title_bar, text="Cookie", variable=self.cookie_var, command=self.on_cookie_toggle,
                      bg='#333333', fg='#aaaaaa', selectcolor='#404040', activebackground='#404040',
                      font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=6)
        
        self.proxy_var = tk.BooleanVar()
        tk.Checkbutton(self.title_bar, text="代理", variable=self.proxy_var, command=self.on_proxy_toggle,
                      bg='#333333', fg='#aaaaaa', selectcolor='#404040', activebackground='#404040',
                      font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=6)
        
        self.mp4_var = tk.BooleanVar()
        tk.Checkbutton(self.title_bar, text="MP4", variable=self.mp4_var,
                      bg='#333333', fg='#aaaaaa', selectcolor='#404040', activebackground='#404040',
                      font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=6)
        
        self.mp3_var = tk.BooleanVar()
        tk.Checkbutton(self.title_bar, text="MP3", variable=self.mp3_var,
                      bg='#333333', fg='#aaaaaa', selectcolor='#404040', activebackground='#404040',
                      font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=6)
        
        # 帮助菜单
        self.help_button = tk.Menubutton(self.title_bar, text="帮助 ▼", bg='#333333', fg='#aaaaaa',
                                        relief=tk.FLAT, bd=0, activebackground='#404040')
        self.help_button.pack(side=tk.LEFT, padx=10)
        self.help_button.menu = tk.Menu(self.help_button, tearoff=0, bg='#2b2b2b', fg='white',
                                       activebackground='#404040', activeforeground='white')
        self.help_button['menu'] = self.help_button.menu
        
        self.help_button.menu.add_command(label="GitHub 仓库", command=self.open_github_repo)
        self.help_button.menu.add_command(label="快速答疑 FAQ", command=self.open_github_faq)
        self.help_button.menu.add_command(label="bilibili 视频教程", command=self.open_bilibili_video)
        self.help_button.menu.add_separator()
        self.help_button.menu.add_command(label="下载 yt-dlp", command=self.get_ytdlp)
        self.help_button.menu.add_command(label="下载 ffmpeg", command=self.get_ffmpeg)
        self.help_button.menu.add_separator()
        self.help_button.menu.add_command(label="升级 yt-dlp", command=self.upgrade_ytdlp)
        
        for child in [self.help_button]:
            child.bind('<Button-1>', self.start_drag)
            child.bind('<B1-Motion>', self.on_drag)
        
        self.title_close = tk.Button(self.title_bar, text="×", font=('Segoe UI', 14, 'bold'),
                                     fg='#888888', bg='#333333', activebackground='#ff4444',
                                     activeforeground='white', relief=tk.FLAT, cursor='hand2',
                                     width=3, command=self.quit_app)
        self.title_close.pack(side=tk.RIGHT, padx=5)
        
        self.download_button = tk.Button(self.title_bar, text="下载", 
                                       command=self.start_download,
                                       font=('Segoe UI', 9, 'bold'),
                                       fg='#00ff00', bg='#333333',
                                       activebackground='#404040', activeforeground='#5dfc5d',
                                       relief=tk.FLAT, cursor='hand2', padx=15)
        self.download_button.pack(side=tk.RIGHT, padx=10)
        
        self.status_frame = ttk.Frame(master, style='TFrame')
        self.status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        self.status_var = tk.StringVar(value="准备就绪")
        self.status_bar = ttk.Label(self.status_frame, textvariable=self.status_var, relief=tk.FLAT, anchor=tk.W)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.style.configure('Status.TLabel', background='#333333', foreground='#aaaaaa', font=('Segoe UI', 9), padding=(10, 2))
        self.status_bar.configure(style='Status.TLabel')
        self.status_frame.configure(style='Status.TLabel') # 给框架也上色

        # 将切换日志和打开文件夹按钮放入状态栏右侧
        self.show_history_var = tk.BooleanVar(value=False)
        self.toggle_button = ttk.Button(self.status_frame, text="显示日志", command=self.toggle_content, style='Status.TButton')
        self.toggle_button.pack(side=tk.RIGHT, padx=2, pady=1)
        
        self.open_folder_button = ttk.Button(self.status_frame, text="打开文件夹", command=self.open_download_folder, style='Status.TButton')
        self.open_folder_button.pack(side=tk.RIGHT, padx=2, pady=1)

        self.stop_button = ttk.Button(self.status_frame, text="停止下载", command=self.stop_all_downloads, style='Status.TButton')
        self.stop_button.pack(side=tk.RIGHT, padx=2, pady=1)
        
        # 设置窗口最小尺寸
        master.update_idletasks()
        master.minsize(500, 400)

        self.queue = queue.Queue()
        self.active_downloads = {}
        self.active_processes = {}
        self.download_counter = 0
        self.master.after(100, self.process_queue)

    def create_menu_bar(self):
        """创建顶部菜单栏（使用 ttk 组件）"""
        # 创建菜单栏框架
        self.menubar_frame = ttk.Frame(self.master)
        self.menubar_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=0, pady=0)
        self.menubar_frame.configure(style='TFrame')
        
        # Help 按钮
        self.help_button = ttk.Menubutton(self.menubar_frame, text="帮助", direction='below')
        self.help_button.pack(side=tk.LEFT, padx=(0, 0))
        
        # 创建 Help 下拉菜单
        help_menu = tk.Menu(self.help_button, tearoff=0, bg='#2b2b2b', fg='white',
                           activebackground='#404040', activeforeground='white',
                           selectcolor='#404040', borderwidth=1)
        self.help_button['menu'] = help_menu
        
        help_menu.add_command(label="GitHub Repository", command=self.open_github_repo)
        help_menu.add_command(label="快速答疑 FAQ", command=self.open_github_faq)
        help_menu.add_command(label="bilibili 视频教程", command=self.open_bilibili_video)
        help_menu.add_separator()
        help_menu.add_command(label="下载 yt-dlp", command=self.get_ytdlp)
        help_menu.add_command(label="下载 ffmpeg", command=self.get_ffmpeg)
        help_menu.add_separator()
        help_menu.add_command(label="升级 yt-dlp", command=self.upgrade_ytdlp)
        
        # 分隔符标签
        separator_label = ttk.Label(self.menubar_frame, text="||", foreground='#888888')
        separator_label.pack(side=tk.LEFT, padx=(8, 8))
        
        # 版本信息标签
        version_label = ttk.Label(self.menubar_frame, text="ytdlpGUI v2.3", foreground='#888888')
        version_label.pack(side=tk.LEFT, padx=(0, 8))
        
        # 配置菜单栏样式
        self.style.configure('TMenubutton', background='#2b2b2b', foreground='white', 
                            borderwidth=0, padding=(8, 4), relief='flat')
        self.style.map('TMenubutton',
                      background=[('active', '#404040'), ('!active', '#2b2b2b'), ('pressed', '#404040')],
                      foreground=[('active', 'white'), ('!active', 'white')],
                      relief=[('active', 'flat'), ('!active', 'flat')])
        
        # 确保菜单栏框架背景是黑色
        self.style.configure('TFrame', background='#464646')
        # 为菜单栏框架单独设置样式
        self.menubar_frame.configure(style='TFrame')


    def toggle_content(self):
        """切换历史记录和日志显示"""
        if self.show_history_var.get():
            self.history_frame.grid_forget()
            self.log_frame.grid()
            self.toggle_button.config(text="显示历史记录")
            self.show_history_var.set(False)
        else:
            self.log_frame.grid_forget()
            self.history_frame.grid()
            self.toggle_button.config(text="显示日志")
            self.show_history_var.set(True)

    def clear_history(self):
        """清空所有历史记录"""
        if messagebox.askyesno("确认", "确定要清空所有历史记录吗？"):
            self.history_data = []
            self.save_history()
            self.update_history_display()
            self.log("历史记录已清空")

    def open_github_repo(self):
        webbrowser.open("https://github.com/cornradio/ytdlpgui")

    def open_github_faq(self):
        webbrowser.open("https://github.com/cornradio/ytdlpgui/blob/main/how-to-use-cookie.md")
    def open_bilibili_video(self):
        webbrowser.open("https://www.bilibili.com/video/BV1oJ7ezEEqK")

    def get_ytdlp(self):
        webbrowser.open('https://github.com/yt-dlp/yt-dlp/wiki/Installation')
    def get_ffmpeg(self):
        webbrowser.open('https://github.com/ffbinaries/ffbinaries-prebuilt/releases')

    def load_history(self):
        """加载历史记录"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history_data = json.load(f)
            else:
                self.history_data = []
            self.update_history_display()
        except Exception as e:
            self.log(f"Error loading history: {e}")
            self.history_data = []

    def save_history(self):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"Error saving history: {e}")

    def update_history_display(self):
        """更新历史记录显示"""
        self.history_listbox.delete(0, tk.END)
        # 按时间倒序显示，最新的在前面
        for item in reversed(self.history_data[-50:]):  # 只显示最近50条
            title = item.get('title', 'Unknown')
            url = item.get('url', '')
            # 截断过长的标题和URL
            if len(title) > 40:
                title = title[:37] + "..."
            if len(url) > 40:
                url = url[:37] + "..."
            display_text = f"{title} | {url}"
            self.history_listbox.insert(0, display_text)

    def add_to_history(self, url, title=None):
        """添加历史记录"""
        # 检查是否已存在相同的URL
        for item in self.history_data:
            if item.get('url') == url:
                # 更新现有记录的时间
                item['timestamp'] = datetime.now().isoformat()
                if title:
                    item['title'] = title
                self.save_history()
                self.update_history_display()
                return
        
        # 添加新记录
        history_item = {
            'url': url,
            'title': title or 'Unknown',
            'timestamp': datetime.now().isoformat()
        }
        self.history_data.append(history_item)
        # 限制历史记录数量，最多保存1000条
        if len(self.history_data) > 1000:
            self.history_data = self.history_data[-1000:]
        self.save_history()
        self.update_history_display()

    def on_history_select(self, event):
        """双击历史记录项时填充URL"""
        selection = self.history_listbox.curselection()
        if selection and self.history_data:
            index = selection[0]
            # 由于显示是倒序的，需要转换索引
            # 只显示最近50条，所以需要计算实际索引
            displayed_count = min(50, len(self.history_data))
            actual_index = len(self.history_data) - 1 - index
            if 0 <= actual_index < len(self.history_data):
                url = self.history_data[actual_index].get('url', '')
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, url)
                title = self.history_data[actual_index].get('title', 'Unknown')
                self.log(f"Selected from history: {title}")
                self.set_status(f"已从历史记录加载: {title}")

    def load_tags(self):
        """加载已保存的 tags"""
        try:
            if os.path.exists('tags_history.json'):
                with open('tags_history.json', 'r', encoding='utf-8') as f:
                    self.tags_data = json.load(f)
            else:
                self.tags_data = []
            self.update_tag_combobox()
        except Exception as e:
            self.log(f"Error loading tags: {e}")
            self.tags_data = []

    def save_tags(self):
        """保存 tags"""
        try:
            with open('tags_history.json', 'w', encoding='utf-8') as f:
                json.dump(self.tags_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"Error saving tags: {e}")

    def update_tag_combobox(self):
        """更新 tag 下拉菜单选项"""
        values = list(self.tags_data)
        self.tag_entry['values'] = values

    def on_tag_select(self, event):
        pass
    
    def clear_all_tags(self):
        """清除所有已保存的 Tag"""
        if not self.tags_data:
            return
        if messagebox.askyesno("确认", "确定要清除所有已保存的 Tag 吗？"):
            self.tags_data = []
            self.save_tags()
            self.update_tag_combobox()
            self.tag_entry.set("")
            self.log("所有标签已清除")

    def open_settings(self):
        """打开 settings.ini 文件"""
        settings_path = os.path.abspath('settings.ini')
        if os.path.exists(settings_path):
            try:
                if os.name == 'nt':  # Windows
                    os.system(f'notepad "{settings_path}"')
                elif os.uname().sysname == 'Darwin':  # macOS
                    subprocess.run(['open', '-a', 'TextEdit', settings_path])
                else:  # Linux
                    subprocess.run(['xdg-open', settings_path])
                self.log(f"opened settings.ini: {settings_path}")
                self.log(f"download_path: {self.download_path}")
                self.log(f"ytdlp_path: {self.ytdlp_path}")
                # 刷新配置文件
                self.config.read('settings.ini')
                self.download_path = self.config.get('Settings', 'download_path')
                self.ytdlp_path = self.config.get('Settings', 'ytdlp_path')
            except Exception as e:
                self.log(f"can't open settings.ini: {e}")
        else:
            self.log(f"settings.ini not found: {settings_path}")
            self.log(f"create settings.ini")
            USERNAME = os.getlogin()
            self.config['Settings'] = {
                'download_path': f'C:\\Users\\{USERNAME}\\Downloads',
                'ytdlp_path': 'yt-dlp'
            }
            with open('settings.ini', 'w') as f:
                self.config.write(f)
            self.open_settings()

    def toggle_proxy_entry(self):
        if self.proxy_var.get():
            self.proxy_entry.delete(0, tk.END)
            self.proxy_entry.insert(0, "127.0.0.1:7890")

    def on_rename_toggle(self):
        if self.rename_var.get():
            self.rename_detail.grid(row=0, column=0, sticky=tk.W)
        else:
            self.rename_detail.grid_forget()

    def on_cookie_toggle(self):
        if self.cookie_var.get():
            self.cookie_detail.grid(row=1, column=0, sticky=tk.W)
        else:
            self.cookie_detail.grid_forget()


    def on_proxy_toggle(self):
        if self.proxy_var.get():
            self.proxy_detail.grid(row=2, column=0, sticky=tk.W)
        else:
            self.proxy_detail.grid_forget()

    def open_cookie_file(self):
        """打开选中的 cookie 文件"""
        selected = self.cookie_combo.get()
        if not selected:
            return
        cookie_path = os.path.join("cookies", selected)
        if os.path.exists(cookie_path):
            try:
                if os.name == 'nt':
                    os.system(f'notepad "{cookie_path}"')
                elif os.uname().sysname == 'Darwin':
                    subprocess.run(['open', '-a', 'TextEdit', cookie_path])
                else:
                    subprocess.run(['xdg-open', cookie_path])
                self.log(f"Opened: {selected}")
            except Exception as e:
                self.log(f"Error opening: {e}")
        self.reload_cookie_files()

    def on_cookie_select(self, event):
        pass  # 下拉只切换，不自动打开
    
    def add_cookie_file(self):
        """在 cookies 文件夹创建新的 cookie 文件"""
        cookies_dir = "cookies"
        if not os.path.exists(cookies_dir):
            os.makedirs(cookies_dir)
        
        name = simpledialog.askstring("新建 Cookie 文件", "请输入文件名（不含扩展名）:")
        if name:
            name = name.strip()
            if not name:
                return
            for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
                name = name.replace(char, '_')
            if not name.endswith('.txt'):
                name = name + '.txt'
            
            file_path = os.path.join(cookies_dir, name)
            if os.path.exists(file_path):
                messagebox.showwarning("文件已存在", f"文件 {name} 已存在")
                return
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("# Netscape HTTP Cookie File\n")
                    f.write("# Edit cookies below\n\n")
                self.log(f"已创建: {name}")
                self.reload_cookie_files()
                self.cookie_combo.set(name)
                self.open_cookie_file()
            except Exception as e:
                self.log(f"创建文件失败: {e}")
                messagebox.showerror("错误", f"创建文件失败: {e}")
    
    def reload_cookie_files(self):
        """扫描 cookies 文件夹下的所有 cookie 文件"""
        self.cookie_files = []
        cookies_dir = "cookies"
        if not os.path.exists(cookies_dir):
            os.makedirs(cookies_dir)
        try:
            for f in os.listdir(cookies_dir):
                if f.endswith('.txt'):
                    self.cookie_files.append(f)
        except:
            pass
        self.cookie_combo['values'] = self.cookie_files
        if self.cookie_files:
            if self.cookie_combo.get() not in self.cookie_files:
                self.cookie_combo.set(self.cookie_files[0])
        else:
            self.cookie_combo.set('')
    
    def delete_cookie_file(self):
        """删除选中的 cookie 文件"""
        selected = self.cookie_combo.get()
        if not selected:
            return
        if messagebox.askyesno("确认删除", f"确定要删除 {selected} 吗？"):
            try:
                file_path = os.path.join("cookies", selected)
                os.remove(file_path)
                self.log(f"已删除: {selected}")
                self.reload_cookie_files()
            except Exception as e:
                self.log(f"删除失败: {e}")
                messagebox.showerror("错误", f"删除失败: {e}")

    def get_video_title(self, url):
        """获取视频标题"""
        try:
            # 构建获取信息的命令
            info_command = [self.ytdlp_path, url, "--print", "%(title)s", "--no-download"]
            
            # 添加代理设置（如果启用）
            if self.proxy_var.get():
                proxy_address = self.proxy_entry.get()
                if proxy_address:
                    info_command.extend(["--proxy", proxy_address])
            
            # 添加cookie设置（如果启用）
            if self.cookie_var.get():
                selected_cookie = self.cookie_combo.get()
                if selected_cookie:
                    cookie_path = os.path.join("cookies", selected_cookie)
                    if os.path.exists(cookie_path):
                        try:
                            temp_cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                            temp_cookie_file.close()
                            shutil.copy2(cookie_path, temp_cookie_file.name)
                            info_command.extend(["--cookies", temp_cookie_file.name])
                        except:
                            pass
            
            result = subprocess.run(info_command, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                title = result.stdout.strip()
                return title if title else None
        except subprocess.TimeoutExpired:
            self.log("Timeout getting video title")
        except Exception as e:
            self.log(f"Could not get video title: {e}")
            self.set_status(f"获取视频信息失败")
        return None

    def start_download(self):
        url = self.url_entry.get()
        
        if not url:
            self.log("Error: Please enter a URL.")
            return
        
        self.add_to_history(url, "获取中...")
        
        thread = threading.Thread(target=self._download_worker, args=(url,))
        thread.daemon = True
        thread.start()
        
    def _download_worker(self, url):
        """后台线程：获取标题 + 执行下载"""
        download_id = self.download_counter + 1
        
        self.queue.put(f"[下载 {download_id}] 正在获取视频信息...")
        
        video_title = self.get_video_title(url)
        if video_title:
            self.add_to_history(url, video_title)
        
        for item in self.history_data:
            if item.get('url') == url:
                item['title'] = video_title if video_title else "Unknown"
                break
        self.save_history()
        self.update_history_display()
        
        short_url = url[:50] + "..." if len(url) > 50 else url
        self.queue.put(f"[下载 {download_id}] 开始: {short_url}")
        
        self.download_counter += 1
        download_id = self.download_counter
        
        command = [self.ytdlp_path, url]
        
        if self.proxy_var.get():
            proxy_address = self.proxy_entry.get()
            if proxy_address:
                command.extend(["--proxy", proxy_address])
        
        if self.cookie_var.get():
            selected_cookie = self.cookie_combo.get()
            if selected_cookie:
                cookie_path = os.path.join("cookies", selected_cookie)
                if os.path.exists(cookie_path):
                    try:
                        temp_cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                        temp_cookie_file.close()
                        shutil.copy2(cookie_path, temp_cookie_file.name)
                        command.extend(["--cookies", temp_cookie_file.name])
                    except:
                        pass
        
        command.extend(["-U"])
        
        if self.mp4_var.get():
            command.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
            command.extend(["--merge-output-format", "mp4"])
        
        if self.mp3_var.get():
            command.extend(["--extract-audio", "--audio-format", "mp3"])
        
        if self.rename_var.get():
            base_name = self.rename_entry.get().strip()
            tag_val = self.tag_entry.get().strip()
            
            if base_name or tag_val:
                if not base_name:
                    new_name = "%(title)s"
                else:
                    new_name = base_name
                
                if tag_val:
                    new_name = f"{new_name}#{tag_val}"
                    if tag_val not in self.tags_data:
                        self.tags_data.append(tag_val)
                        self.master.after(0, self.save_tags)
                        self.master.after(0, self.update_tag_combobox)
                
                for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
                    new_name = new_name.replace(char, '_')
                command.extend(["-o", f"{new_name}.%(ext)s"])
            else:
                command.extend(["-o", "%(title)s-%(id)s.%(ext)s"])
        else:
            command.extend(["-o", "%(title)s-%(id)s.%(ext)s"])
        
        command.extend(["-P", self.download_path])
        
        self.run_download_process(command, download_id, url)

    def run_download_process(self, command, download_id, url):
        """在新线程中运行下载进程，实时输出到GUI"""
        process = None
        try:
            if os.name == 'nt':
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                self.active_processes[download_id] = process
                
                for line in iter(process.stdout.readline, ''):
                    if self.active_processes.get(download_id) is None:
                        break
                    if line:
                        self.queue.put(f"[下载 {download_id}] {line.rstrip()}")
                    if process.poll() is not None:
                        break
                process.stdout.close()
                process.wait()
                return_code = process.returncode
                
            else:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    shell=True
                )
                
                self.active_processes[download_id] = process
                
                for line in iter(process.stdout.readline, ''):
                    if self.active_processes.get(download_id) is None:
                        break
                    if line:
                        self.queue.put(f"[下载 {download_id}] {line.rstrip()}")
                    if process.poll() is not None:
                        break
                process.stdout.close()
                return_code = process.wait()
            
            if download_id in self.active_processes:
                del self.active_processes[download_id]
            
            if return_code in (0, 1):
                self.queue.put(f"[下载 {download_id}] 完成!")
                self.master.after(0, lambda: self.set_status(f"下载 {download_id} 完成", duration=5000))
            else:
                self.queue.put(f"[下载 {download_id}] 失败 (错误码: {return_code})")
                self.master.after(0, lambda: self.set_status(f"下载 {download_id} 失败", duration=5000))
                
        except Exception as e:
            self.queue.put(f"[下载 {download_id}] 错误: {e}")
            if download_id in self.active_processes:
                del self.active_processes[download_id]
        finally:
            if download_id in self.active_downloads:
                del self.active_downloads[download_id]

    def stop_all_downloads(self):
        """停止所有正在进行的下载"""
        if not self.active_processes:
            self.set_status("没有正在下载的任务", duration=2000)
            return
        
        stopped_count = 0
        for download_id, process in list(self.active_processes.items()):
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    process.terminate()
                stopped_count += 1
                self.queue.put(f"[下载 {download_id}] 已停止")
            except Exception as e:
                self.queue.put(f"[下载 {download_id}] 停止失败: {e}")
        
        self.active_processes.clear()
        if stopped_count > 0:
            self.set_status(f"已停止 {stopped_count} 个下载任务", duration=3000)

    def upgrade_ytdlp(self):
        """升级 yt-dlp（后台执行）"""
        self.log("正在检查 yt-dlp 版本...")
        self.set_status("正在检查版本...")
        
        thread = threading.Thread(target=self._upgrade_worker)
        thread.daemon = True
        thread.start()
    
    def _upgrade_worker(self):
        """后台线程：升级 yt-dlp 并显示结果"""
        try:
            result = subprocess.run([self.ytdlp_path, "--version"], 
                                   capture_output=True, text=True, timeout=10)
            current_version = result.stdout.strip() if result.returncode == 0 else "未知"
            self.queue.put(f"当前版本: {current_version}")
            
            self.queue.put("正在升级 yt-dlp...")
            
            upgrade_result = subprocess.run(["pipx", "upgrade", "yt-dlp"],
                                          capture_output=True, text=True, timeout=120)
            
            if upgrade_result.returncode == 0:
                self.queue.put("升级成功!")
            else:
                self.queue.put(f"升级失败: {upgrade_result.stderr}")
                return
            
            result = subprocess.run([self.ytdlp_path, "--version"],
                                  capture_output=True, text=True, timeout=10)
            new_version = result.stdout.strip() if result.returncode == 0 else "未知"
            self.queue.put(f"新版本: {new_version}")
            
            latest_result = subprocess.run(["pipx", "run", "yt-dlp", "--version"],
                                          capture_output=True, text=True, timeout=15)
            latest_version = latest_result.stdout.strip() if latest_result.returncode == 0 else None
            
            if latest_version:
                if new_version == latest_version:
                    self.queue.put(f"✓ 已是最新版本 (最新: {latest_version})")
                    self.master.after(0, lambda: self.set_status("yt-dlp 已是最新", duration=5000))
                else:
                    self.queue.put(f"⚠ 发现新版本: {latest_version} (当前: {new_version})")
                    self.master.after(0, lambda: self.set_status(f"有新版本可用: {latest_version}", duration=5000))
            else:
                self.queue.put(f"无法获取最新版本信息")
                
        except subprocess.TimeoutExpired:
            self.queue.put("升级超时，请重试")
        except Exception as e:
            self.queue.put(f"升级出错: {e}")

    def run_yt_dlp(self, command):
        # 这个方法不再需要，因为我们直接在CMD窗口中执行命令
        pass

    def enable_open_folder_button(self):
        # This method now primarily ensures the button is normal.
        # If self.download_path is None, clicking it will log a message.
        self.open_folder_button.config(state=tk.NORMAL)

    def open_download_folder(self):
        if self.download_path and os.path.isdir(self.download_path): # Check if path exists and is a directory
            try:
                if os.name == 'nt': 
                    os.startfile(os.path.realpath(self.download_path))
                elif os.uname().sysname == 'Darwin': 
                    subprocess.run(['open', self.download_path], check=True)
                else: 
                    subprocess.run(['xdg-open', self.download_path], check=True)
            except FileNotFoundError: # Should be caught by os.path.isdir, but as a fallback
                 self.log(f"Error: Download folder not found at {self.download_path}")
            except Exception as e:
                self.log(f"Could not open folder: {e}. Please open manually: {self.download_path}")
        elif self.download_path: # Path was set but is not a valid directory
            self.log(f"Error: Download path '{self.download_path}' is not a valid directory or does not exist.")
        else: # No download path has been set yet
            self.log("No download directory has been selected yet.")

    def show_last_downloaded_file(self):
        if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
            try:
                if os.name == 'nt':
                    # Windows系统下使用explorer选中文件
                    subprocess.run(['explorer', '/select,', self.last_downloaded_file], check=True)
                elif os.uname().sysname == 'Darwin':
                    # macOS系统下使用open命令
                    subprocess.run(['open', '-R', self.last_downloaded_file], check=True)
                else:
                    # Linux系统下使用xdg-open
                    subprocess.run(['xdg-open', os.path.dirname(self.last_downloaded_file)], check=True)
            except Exception as e:
                self.log(f"无法显示文件: {e}")
        else:
            self.log("没有找到最后下载的文件")

    def clear_url(self):
        self.url_entry.delete(0, tk.END)

    def log(self, message):
        self.queue.put(message)

    def set_status(self, message, duration=3000):
        """设置状态栏信息，duration 毫秒后恢复"""
        self.status_var.set(message)
        # 取消之前的恢复任务（如果有）
        if hasattr(self, '_status_timer'):
            self.master.after_cancel(self._status_timer)
        self._status_timer = self.master.after(duration, lambda: self.status_var.set("准备就绪"))

    def clean_url_params(self):
        """手动删除 URL 中的参数 (?)"""
        url = self.url_var.get().strip()
        if '?' in url:
            base_url = url.split('?')[0]
            if base_url != url:
                self.url_var.set(base_url)
                self.set_status("已手动删除 URL 中的冗余参数 (?)")
                self.log(f"Cleaned URL: {base_url}")
    
    def quit_app(self):
        """退出程序前停止所有下载"""
        for process in list(self.active_processes.values()):
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    process.terminate()
            except:
                pass
        self.master.destroy()
    
    def start_drag(self, event):
        self.x = event.x
        self.y = event.y
    
    def on_drag(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.master.winfo_x() + deltax
        y = self.master.winfo_y() + deltay
        self.master.geometry(f'+{x}+{y}')

    def process_queue(self):
        try:
            while True:
                message = self.queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.config(state=tk.DISABLED)
                self.log_text.see(tk.END)
                self.queue.task_done()
        except queue.Empty:
            pass
        self.master.after(100, self.process_queue)

if __name__ == '__main__':
    import screeninfo
    root = ThemedTk(theme="equilux")
    root.configure(bg='#2b2b2b')
    # root.overrideredirect(True)
    root.resizable(True, True)
    
    screen = screeninfo.get_monitors()[0]
    x = (screen.width - 1000) // 2
    y = (screen.height - 800) // 2
    root.geometry(f'1000x800+{x}+{y}')
    
    root.iconbitmap(resource_path("icon.ico"))
        
    gui = YtDlpGUI(root)
    root.mainloop()
