import gradio as gr
import subprocess
import os
import sys
import json
import configparser
from datetime import datetime

CONFIG_FILE = 'settings.ini'
HISTORY_FILE = 'download_history.json'
TAGS_FILE = 'tags_history.json'
COOKIES_DIR = 'cookies'


class YtDlpApp:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.load_config()
        self.history_data = []
        self.tags_data = []
        self.cookie_files = []
        self.active_process = None
        self.load_history()
        self.load_tags()
        self.reload_cookies()

    def load_config(self):
        try:
            self.config.read(CONFIG_FILE)
            if 'Settings' in self.config:
                self.download_path = self.config.get('Settings', 'download_path', fallback=self.get_default_download_path())
                self.ytdlp_path = self.config.get('Settings', 'ytdlp_path', fallback='yt-dlp')
            else:
                self.download_path = self.get_default_download_path()
                self.ytdlp_path = 'yt-dlp'
        except:
            self.download_path = self.get_default_download_path()
            self.ytdlp_path = 'yt-dlp'

    def get_default_download_path(self):
        if os.name == 'nt':
            return os.path.join(os.path.expanduser("~"), "Downloads")
        return os.path.expanduser("~/Downloads")

    def load_history(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.history_data = json.load(f)
        except:
            self.history_data = []

    def save_history(self):
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history_data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_tags(self):
        try:
            if os.path.exists(TAGS_FILE):
                with open(TAGS_FILE, 'r', encoding='utf-8') as f:
                    self.tags_data = json.load(f)
        except:
            self.tags_data = []

    def save_tags(self):
        try:
            with open(TAGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.tags_data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def reload_cookies(self):
        if not os.path.exists(COOKIES_DIR):
            os.makedirs(COOKIES_DIR)
        self.cookie_files = sorted([f for f in os.listdir(COOKIES_DIR) if f.endswith('.txt')])

    def add_to_history(self, url, title):
        for item in self.history_data:
            if item.get('url') == url:
                item['timestamp'] = datetime.now().isoformat()
                item['title'] = title
                self.save_history()
                return
        self.history_data.append({
            'url': url,
            'title': title or 'Unknown',
            'timestamp': datetime.now().isoformat()
        })
        if len(self.history_data) > 1000:
            self.history_data = self.history_data[-1000:]
        self.save_history()

    def download(self, url, use_mp4, use_mp3, rename, tag, proxy, use_cookie, cookie_file, download_path):
        if not url or not url.strip():
            return "请输入 URL", self.get_history_display()

        os.makedirs(download_path, exist_ok=True)

        command = [self.ytdlp_path, url]

        if proxy and proxy.strip():
            command.extend(["--proxy", proxy.strip()])

        if use_cookie and cookie_file:
            cookie_path = os.path.join(COOKIES_DIR, cookie_file)
            if os.path.exists(cookie_path):
                command.extend(["--cookies", cookie_path])

        if use_mp4:
            command.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
            command.extend(["--merge-output-format", "mp4"])

        if use_mp3:
            command.extend(["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"])

        if rename.strip() or tag.strip():
            new_name = rename.strip() if rename.strip() else "%(title)s"
            if tag.strip():
                new_name = f"{new_name}#{tag.strip()}"
                if tag.strip() not in self.tags_data:
                    self.tags_data.append(tag.strip())
                    self.save_tags()
            for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
                new_name = new_name.replace(char, '_')
            command.extend(["-o", f"{new_name}.%(ext)s"])
        else:
            command.extend(["-o", "%(title)s-%(id)s.%(ext)s"])

        command.extend(["-P", download_path])

        title = self.get_title(url, proxy.strip() if proxy.strip() else None)
        self.add_to_history(url, title or "Unknown")

        output = []
        output.append(f"[开始] {url}")
        output.append(f"[路径] {download_path}")

        try:
            self.active_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            for line in iter(self.active_process.stdout.readline, ''):
                if line:
                    line = line.rstrip()
                    if len(line) > 200:
                        line = line[:200] + "..."
                    output.append(line)
                    if len(output) > 100:
                        output = output[-100:]
                if self.active_process.poll() is not None:
                    break

            self.active_process.wait()
            return_code = self.active_process.returncode
            self.active_process = None

            if return_code == 0:
                output.append("[完成] 下载成功!")
            elif return_code == 1:
                output.append("[完成] 下载完成(有警告)")
            else:
                output.append(f"[失败] 错误码: {return_code}")

        except FileNotFoundError:
            output.append("[错误] 找不到 yt-dlp，请确保已安装")
        except Exception as e:
            output.append(f"[错误] {str(e)}")

        return "\n".join(output), self.get_history_display()

    def get_title(self, url, proxy=None):
        try:
            cmd = [self.ytdlp_path, "--print", "%(title)s", "--no-download", url]
            if proxy:
                cmd.extend(["--proxy", proxy])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None

    def stop_download(self):
        if self.active_process:
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.active_process.pid)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    self.active_process.terminate()
                self.active_process = None
                return "[停止] 已停止下载"
            except:
                self.active_process = None
                return "[停止] 已停止下载"
        return "[提示] 没有正在下载的任务"

    def clear_history(self):
        self.history_data = []
        self.save_history()
        return "[完成] 历史记录已清空"

    def get_history_display(self):
        if not self.history_data:
            return "暂无历史记录"
        lines = []
        for item in reversed(self.history_data[-20:]):
            title = item.get('title', 'Unknown')
            url = item.get('url', '')
            if len(title) > 30:
                title = title[:27] + "..."
            if len(url) > 50:
                url = url[:47] + "..."
            lines.append(f"{title}")
            lines.append(f"  {url}")
        return "\n".join(lines)

    def create_cookie(self, name):
        if not name or not name.strip():
            return "请输入文件名"
        filename = name.strip()
        for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
            filename = filename.replace(char, '_')
        if not filename.endswith('.txt'):
            filename = filename + '.txt'
        file_path = os.path.join(COOKIES_DIR, filename)
        if os.path.exists(file_path):
            return f"文件已存在: {filename}"
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n\n")
            self.reload_cookies()
            return f"已创建: {filename}"
        except Exception as e:
            return f"创建失败: {e}"

    def delete_cookie(self, filename):
        if not filename:
            return "请选择要删除的文件"
        file_path = os.path.join(COOKIES_DIR, filename)
        try:
            os.remove(file_path)
            self.reload_cookies()
            return f"已删除: {filename}"
        except Exception as e:
            return f"删除失败: {e}"

    def open_folder(self):
        path = self.download_path
        if os.path.exists(path):
            try:
                if os.name == 'nt':
                    os.startfile(path)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', path])
                else:
                    subprocess.run(['xdg-open', path])
            except:
                pass
        return f"已打开: {path}"

    def upgrade_ytdlp(self):
        output = []
        output.append("[检查] yt-dlp 版本...")
        try:
            result = subprocess.run([self.ytdlp_path, "--version"],
                                  capture_output=True, text=True, timeout=10)
            current = result.stdout.strip() if result.returncode == 0 else "未知"
            output.append(f"当前版本: {current}")

            output.append("[升级] 正在升级...")
            upgrade = subprocess.run(["pip", "install", "--upgrade", "yt-dlp"],
                                    capture_output=True, text=True, timeout=120)
            if upgrade.returncode == 0:
                output.append("升级成功!")
            else:
                output.append(f"升级失败: {upgrade.stderr[:100]}")

            result = subprocess.run([self.ytdlp_path, "--version"],
                                  capture_output=True, text=True, timeout=10)
            new = result.stdout.strip() if result.returncode == 0 else "未知"
            output.append(f"新版本: {new}")
        except subprocess.TimeoutExpired:
            output.append("升级超时")
        except Exception as e:
            output.append(f"错误: {e}")
        return "\n".join(output)

    def get_cookie_files_list(self):
        return self.cookie_files

    def get_tags_list(self):
        return self.tags_data


def create_ui():
    app = YtDlpApp()

    with gr.Blocks(title="yt-dlp GUI", fill_height=True) as demo:
        gr.Markdown("# yt-dlp Downloader")
        gr.Markdown(f"下载目录: `{app.download_path}`")

        with gr.Row(equal_height=False):
            with gr.Column(scale=3, min_width=400):
                with gr.Group():
                    gr.Markdown("### 下载")
                    url_input = gr.Textbox(
                        label="URL",
                        placeholder="输入视频链接",
                        lines=1,
                        scale=3
                    )
                    with gr.Row():
                        download_btn = gr.Button("下载", variant="primary", scale=1)
                        stop_btn = gr.Button("停止", scale=1)

                with gr.Group():
                    gr.Markdown("### 格式选项")
                    with gr.Row():
                        use_mp4 = gr.Checkbox(label="MP4", value=False, scale=1)
                        use_mp3 = gr.Checkbox(label="MP3", value=False, scale=1)

                with gr.Group():
                    gr.Markdown("### 高级选项")
                    with gr.Row():
                        with gr.Column(scale=2):
                            rename_input = gr.Textbox(
                                label="重命名",
                                placeholder="留空使用默认命名",
                                lines=1
                            )
                        with gr.Column(scale=1):
                            tag_input = gr.Dropdown(
                                label="标签",
                                choices=app.get_tags_list(),
                                allow_custom_value=True
                            )
                    with gr.Row():
                        with gr.Column(scale=2):
                            proxy_input = gr.Textbox(
                                label="代理",
                                placeholder="如: 127.0.0.1:7890",
                                lines=1
                            )
                        with gr.Column(scale=1):
                            path_input = gr.Textbox(
                                label="路径",
                                value=app.download_path,
                                lines=1
                            )
                    with gr.Row():
                        with gr.Column(scale=1):
                            use_cookie = gr.Checkbox(label="Cookie", value=False)
                        with gr.Column(scale=2):
                            cookie_select = gr.Dropdown(
                                label="Cookie文件",
                                choices=app.get_cookie_files_list(),
                                visible=False
                            )

                with gr.Group():
                    gr.Markdown("### 工具")
                    with gr.Row():
                        open_folder_btn = gr.Button("打开文件夹", size="compact")
                        upgrade_btn = gr.Button("升级yt-dlp", size="compact")
                        clear_history_btn = gr.Button("清空历史", size="compact")
                    cookie_msg = gr.Textbox(label="状态", lines=1, interactive=False)

            with gr.Column(scale=2, min_width=300):
                gr.Markdown("### 历史记录")
                history_display = gr.Textbox(
                    value=app.get_history_display(),
                    lines=15,
                    interactive=False
                )
                with gr.Row():
                    cookie_name = gr.Textbox(label="新建Cookie", placeholder="文件名", lines=1, scale=2)
                    create_cookie_btn = gr.Button("+", size="compact", scale=1)
                    delete_cookie_btn = gr.Button("删除", size="compact", scale=1)

        gr.Markdown("---")
        gr.Markdown("### 下载日志")
        output_display = gr.Textbox(
            value="准备就绪...",
            lines=8,
            interactive=False
        )

        def toggle_cookie(checked):
            return gr.update(visible=checked)

        use_cookie.change(
            fn=toggle_cookie,
            inputs=[use_cookie],
            outputs=[cookie_select]
        )

        def do_download(url, mp4, mp3, rename, tag, proxy, cookie, cookie_file, path):
            result, history = app.download(url, mp4, mp3, rename, tag, proxy, cookie, cookie_file, path)
            return result, history

        download_btn.click(
            fn=do_download,
            inputs=[url_input, use_mp4, use_mp3, rename_input, tag_input,
                   proxy_input, use_cookie, cookie_select, path_input],
            outputs=[output_display, history_display]
        )

        stop_btn.click(
            fn=lambda: (app.stop_download(), app.get_history_display()),
            outputs=[output_display, history_display]
        )

        clear_history_btn.click(
            fn=app.clear_history,
            outputs=[cookie_msg]
        )

        open_folder_btn.click(
            fn=app.open_folder,
            outputs=[cookie_msg]
        )

        upgrade_btn.click(
            fn=app.upgrade_ytdlp,
            outputs=[output_display]
        )

        create_cookie_btn.click(
            fn=app.create_cookie,
            inputs=[cookie_name],
            outputs=[cookie_msg]
        ).then(
            fn=lambda: (gr.update(choices=app.get_cookie_files_list()), ""),
            outputs=[cookie_select, cookie_name]
        )

        delete_cookie_btn.click(
            fn=app.delete_cookie,
            inputs=[cookie_select],
            outputs=[cookie_msg]
        ).then(
            fn=lambda: gr.update(choices=app.get_cookie_files_list()),
            outputs=[cookie_select]
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)