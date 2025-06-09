import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')

class PhotoSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("照片分類器 - 固定尺寸+置中修正")

        self.window_width = 1200
        self.window_height = 800
        self.center_window(self.window_width, self.window_height)

        # 主框架
        main_frame = tk.Frame(root)
        main_frame.pack(padx=10, pady=10, expand=True, fill="both")

        # 左側按鈕
        btn_frame = tk.Frame(main_frame)
        btn_frame.grid(row=0, column=0, padx=10, sticky="n")

        self.undo_button = tk.Button(btn_frame, text="🔙 回上一張 (Backspace)", command=self.undo_move, width=20)
        self.undo_button.pack(pady=5)

        self.exit_button = tk.Button(btn_frame, text="🚪 先做到這邊 (Esc)", command=self.exit_program, width=20)
        self.exit_button.pack(pady=5)

        self.no_button = tk.Button(btn_frame, text="❌ 不喜歡 (左鍵)", command=self.move_to_no, width=20)
        self.no_button.pack(pady=5)

        self.yes_button = tk.Button(btn_frame, text="❤️ 喜歡 (右鍵)", command=self.move_to_yes, width=20)
        self.yes_button.pack(pady=5)

        # 右側圖片顯示
        self.image_label = tk.Label(main_frame)
        self.image_label.grid(row=0, column=1)
        self.image_label.bind("<Button-1>", lambda e: self.root.focus_set())  # 點圖片恢復 focus

        # 鍵盤快捷鍵
        self.root.bind_all("<Left>", lambda e: self.move_to_no())
        self.root.bind_all("<Right>", lambda e: self.move_to_yes())
        self.root.bind_all("<BackSpace>", lambda e: self.undo_move())
        self.root.bind_all("<Escape>", lambda e: self.exit_program())

        # 狀態初始化
        self.folder = ''
        self.image_files = []
        self.current_index = 0
        self.history = []

        self.root.after_idle(self.setup_folder)

    def center_window(self, width, height):
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max((screen_w - width) // 2, 0)
        y = max((screen_h - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def exit_program(self):
        self.root.quit()

    def setup_folder(self):
        folder = filedialog.askdirectory(title="選擇圖片資料夾")
        if not folder:
            self.root.quit()
            return
        self.folder = folder
        self.yes_folder = os.path.join(folder, "Yes")
        self.no_folder = os.path.join(folder, "No")
        os.makedirs(self.yes_folder, exist_ok=True)
        os.makedirs(self.no_folder, exist_ok=True)

        self.image_files = [f for f in os.listdir(folder)
                            if f.lower().endswith(SUPPORTED_FORMATS)
                            and os.path.isfile(os.path.join(folder, f))]
        if not self.image_files:
            messagebox.showinfo("提示", "找不到圖片檔案")
            self.root.quit()
            return

        self.current_index = 0
        self.show_image()

    def show_image(self):
        if self.current_index >= len(self.image_files):
            messagebox.showinfo("完成", "所有圖片已分類完成！")
            self.root.quit()
            return
        image_path = os.path.join(self.folder, self.image_files[self.current_index])
        img = Image.open(image_path)

        # 將圖片縮放到固定大小範圍內
        display_width = 900
        display_height = 700
        img.thumbnail((display_width, display_height))

        self.tk_img = ImageTk.PhotoImage(img)
        self.image_label.config(image=self.tk_img)

    def move_current_file(self, destination_folder):
        filename = self.image_files[self.current_index]
        src = os.path.join(self.folder, filename)
        dst = os.path.join(destination_folder, filename)
        shutil.move(src, dst)
        self.history.append((filename, destination_folder))
        self.current_index += 1
        self.show_image()

    def move_to_yes(self):
        self.move_current_file(self.yes_folder)

    def move_to_no(self):
        self.move_current_file(self.no_folder)

    def undo_move(self):
        if not self.history:
            return
        last_filename, from_folder = self.history.pop()
        dst = os.path.join(self.folder, last_filename)
        src = os.path.join(from_folder, last_filename)
        if os.path.exists(src):
            shutil.move(src, dst)
            self.current_index -= 1
            self.show_image()

# 啟動應用
root = tk.Tk()
app = PhotoSorterApp(root)

# 滑鼠點擊分類功能（整個視窗有效）
root.bind("<Button-1>", lambda e: app.move_to_no())   # 左鍵 = 不喜歡
root.bind("<Button-3>", lambda e: app.move_to_yes())  # 右鍵 = 喜歡

root.mainloop()
