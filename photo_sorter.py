import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')

class PhotoSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📂 照片分類器 Photo Sorter")
        self.window_width = 1200
        self.window_height = 850
        self.center_window(self.window_width, self.window_height)

        self.root.configure(bg="#1e1e1e")

        # 主框架（圖片置中）
        self.main_frame = tk.Frame(root, bg="#1e1e1e")
        self.main_frame.pack(expand=True, fill="both")

        self.image_label = tk.Label(self.main_frame, bg="#1e1e1e")
        self.image_label.place(relx=0.5, rely=0.5, anchor="center")
        self.image_label.bind("<Button-1>", lambda e: self.root.focus_set())

        # 底部按鈕列
        btn_frame = tk.Frame(root, bg="#2e2e2e")
        btn_frame.pack(side="bottom", fill="x", pady=10)

        button_style = {"bg": "#3e3e3e", "fg": "white", "activebackground": "#5e5e5e", "activeforeground": "white", "width": 20}

        self.undo_button = tk.Button(btn_frame, text="🔙 回上一張 (Backspace)", command=self.undo_move, **button_style)
        self.undo_button.pack(side="left", padx=10, pady=5)

        self.no_button = tk.Button(btn_frame, text="❌ 不喜歡 (左鍵)", command=self.move_to_no, **button_style)
        self.no_button.pack(side="left", padx=10, pady=5)

        self.yes_button = tk.Button(btn_frame, text="❤️ 喜歡 (右鍵)", command=self.move_to_yes, **button_style)
        self.yes_button.pack(side="left", padx=10, pady=5)

        self.exit_button = tk.Button(btn_frame, text="🚪 先做到這邊 (Esc)", command=self.exit_program, **button_style)
        self.exit_button.pack(side="right", padx=10, pady=5)

        # 快捷鍵
        self.root.bind_all("<Left>", lambda e: self.move_to_no())
        self.root.bind_all("<Right>", lambda e: self.move_to_yes())
        self.root.bind_all("<BackSpace>", lambda e: self.undo_move())
        self.root.bind_all("<Escape>", lambda e: self.exit_program())

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
        display_width = 900
        display_height = 700
        img.thumbnail((display_width, display_height))

        self.tk_img = ImageTk.PhotoImage(img)
        self.image_label.config(image=self.tk_img)
        self.image_label.place(relx=0.5, rely=0.5, anchor="center")

    def animate_slide_out(self, direction="left", callback=None):
        steps = 15
        delta = -60 if direction == "left" else 60
        count = 0

        def slide():
            nonlocal count
            if count < steps:
                self.image_label.place_configure(x=self.image_label.winfo_x() + delta)
                count += 1
                self.root.after(10, slide)
            else:
                self.image_label.place_forget()
                if callback:
                    callback()
                self.image_label.place(relx=0.5, rely=0.5, anchor="center")

        self.image_label.place(relx=0.5, rely=0.5, anchor="center")
        slide()

    def move_current_file(self, destination_folder):
        filename = self.image_files[self.current_index]
        src = os.path.join(self.folder, filename)
        dst = os.path.join(destination_folder, filename)
        shutil.move(src, dst)
        self.history.append((filename, destination_folder))
        self.current_index += 1
        self.show_image()

    def move_to_yes(self):
        self.animate_slide_out("right", lambda: self.move_current_file(self.yes_folder))

    def move_to_no(self):
        self.animate_slide_out("left", lambda: self.move_current_file(self.no_folder))

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

# 滑鼠點擊分類功能
root.bind("<Button-1>", lambda e: app.move_to_no())
root.bind("<Button-3>", lambda e: app.move_to_yes())

root.mainloop()
