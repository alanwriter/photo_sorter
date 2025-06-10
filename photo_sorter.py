import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from imagededup.methods import CNN

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')

class PhotoSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📂 照片分類器 Photo Sorter")
        self.window_width = 1200
        self.window_height = 850
        self.center_window(self.window_width, self.window_height)
        self.root.configure(bg="#1e1e1e")

        self.main_frame = tk.Frame(root, bg="#1e1e1e")
        self.main_frame.pack(expand=True, fill="both")

        # 左側圖片瀏覽
        self.left_canvas = tk.Canvas(self.main_frame, bg="#1e1e1e", width=160, highlightthickness=0, bd=0)
        self.left_inner_frame = tk.Frame(self.left_canvas, bg="#1e1e1e")
        self.left_scroll = tk.Scrollbar(self.main_frame, orient="vertical", command=self.left_canvas.yview, width=0)
        self.left_canvas.configure(yscrollcommand=self.left_scroll.set)
        self.left_canvas.create_window((0, 0), window=self.left_inner_frame, anchor="nw")
        self.left_inner_frame.bind("<Configure>", lambda e: self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all")))
        self.left_canvas.place(relx=0.0, rely=0.5, anchor="w", height=800)
        self.left_scroll.place_forget()
        self.bind_scroll_events(self.left_canvas)

        # 中間主圖
        self.image_label = tk.Label(self.main_frame, bg="#1e1e1e")
        self.image_label.place(relx=0.5, rely=0.5, anchor="center")
        self.image_label.bind("<Button-1>", lambda e: self.move_to_no())
        self.image_label.bind("<Button-3>", lambda e: self.move_to_yes())

        # 右側相似圖
        self.similar_canvas = tk.Canvas(self.main_frame, bg="#1e1e1e", width=250, highlightthickness=0, bd=0)
        self.similar_inner_frame = tk.Frame(self.similar_canvas, bg="#1e1e1e")
        self.similar_scroll = tk.Scrollbar(self.main_frame, orient="vertical", command=self.similar_canvas.yview, width=0)
        self.similar_canvas.configure(yscrollcommand=self.similar_scroll.set)
        self.similar_canvas.create_window((0, 0), window=self.similar_inner_frame, anchor="nw")
        self.similar_inner_frame.bind("<Configure>", lambda e: self.similar_canvas.configure(scrollregion=self.similar_canvas.bbox("all")))
        self.similar_canvas.place(relx=1.0, rely=0.5, anchor="e", height=800, x= 160)
        self.similar_scroll.place_forget()
        self.bind_scroll_events(self.similar_canvas)

        # 加上這段
        self.similar_canvas.bind(
            "<Configure>",
            lambda e: self.similar_inner_frame.config(width=self.similar_canvas.winfo_width())
        )

        # 按鈕列
        btn_frame = tk.Frame(root, bg="#2e2e2e")
        btn_frame.pack(side="bottom", fill="x", pady=10)
        style = {"bg": "#3e3e3e", "fg": "white", "activebackground": "#5e5e5e", "activeforeground": "white", "width": 20}
        tk.Button(btn_frame, text="🔙 回上一張 (Backspace)", command=self.undo_move, **style).pack(side="left", padx=10, pady=5)
        tk.Button(btn_frame, text="❌ 不喜歡 (左鍵)", command=self.move_to_no, **style).pack(side="left", padx=10, pady=5)
        tk.Button(btn_frame, text="❤️ 喜歡 (右鍵)", command=self.move_to_yes, **style).pack(side="left", padx=10, pady=5)
        tk.Button(btn_frame, text="🚪 先做到這邊 (Esc)", command=self.exit_program, **style).pack(side="right", padx=10, pady=5)
        # 顯示目前檔名的「假按鈕」
        self.filename_display = tk.Label(
            btn_frame,
            text="",
            bg="#3e3e3e",
            fg="white",
            width=40,
            anchor="center",
            relief="groove",
            padx=5,
            pady=5
        )
        self.filename_display.pack(side="left", padx=10)

        self.root.bind_all("<Left>", lambda e: self.move_to_no())
        self.root.bind_all("<Right>", lambda e: self.move_to_yes())
        self.root.bind_all("<BackSpace>", lambda e: self.undo_move())
        self.root.bind_all("<Escape>", lambda e: self.exit_program())

        self.folder = ''
        self.image_files = []
        self.current_index = 0
        self.history = []
        self.duplicates = {}
        self.thumbs = {}

        self.root.after_idle(self.setup_folder)

    def center_window(self, width, height):
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{width}x{height}+{(sw - width)//2}+{(sh - height)//2}")

    def bind_scroll_events(self, canvas):
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", lambda ev: canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

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
        self.image_files = [f for f in os.listdir(folder) if f.lower().endswith(SUPPORTED_FORMATS) and os.path.isfile(os.path.join(folder, f))]
        if not self.image_files:
            messagebox.showinfo("提示", "找不到圖片檔案")
            self.root.quit()
            return

        cnn = CNN()
        self.encodings = cnn.encode_images(image_dir=self.folder)
        self.duplicates = cnn.find_duplicates(encoding_map=self.encodings, min_similarity_threshold=0.9, scores=True)

        for i, fname in enumerate(self.image_files):
            path = os.path.join(self.folder, fname)
            try:
                img = Image.open(path)
                img.thumbnail((80, 80))
                thumb = ImageTk.PhotoImage(img)
                self.thumbs[fname] = thumb
                lbl = tk.Label(self.left_inner_frame, image=thumb, bg="#1e1e1e")
                lbl.image = thumb
                lbl.pack(pady=4)
                def bind_thumb(l=lbl, idx=i):
                    l.bind("<Button-1>", lambda e: self.jump_to_index(idx))
                bind_thumb()
            except:
                continue

        self.current_index = 0
        self.show_image()

    def show_image(self):
        if self.current_index >= len(self.image_files):
            messagebox.showinfo("完成", "所有圖片已分類完成！")
            self.root.quit()
            return
        image_path = os.path.join(self.folder, self.image_files[self.current_index])
        img = Image.open(image_path)
        img.thumbnail((900, 700))
        self.tk_img = ImageTk.PhotoImage(img)
        self.image_label.config(image=self.tk_img)
        self.image_label.place(relx=0.5, rely=0.5, anchor="center")
        self.image_label.lift()
        self.filename_display.config(text=self.image_files[self.current_index])
        self.show_similar_images(self.image_files[self.current_index])

    def show_similar_images(self, current_filename):
        for widget in self.similar_inner_frame.winfo_children():
            widget.destroy()

        if current_filename not in self.duplicates:
            return

        def load():
            for fname, score in sorted(self.duplicates[current_filename], key=lambda x: -x[1]):
                path = os.path.join(self.folder, fname)
                if not os.path.exists(path):
                    continue
                try:
                    thumb = self.thumbs.get(fname)
                    if not thumb:
                        img = Image.open(path)
                        img.thumbnail((80, 80))
                        thumb = ImageTk.PhotoImage(img)
                        self.thumbs[fname] = thumb

                    def add_thumb(t=thumb, f=fname):
                        lbl = tk.Label(self.similar_inner_frame, image=t, bg="#1e1e1e")
                        lbl.image = t
                        lbl.pack(pady=4)
                        lbl.bind("<Button-1>", lambda e: self.jump_to_image(f))

                    self.root.after(0, add_thumb)
                except:
                    continue

        threading.Thread(target=load, daemon=True).start()

    def jump_to_image(self, filename):
        if filename in self.image_files:
            self.current_index = self.image_files.index(filename)
            self.show_image()

    def jump_to_index(self, index):
        if 0 <= index < len(self.image_files):
            self.current_index = index
            self.show_image()

    def animate_swipe(self, direction, callback):
        start_x = 0.5
        end_x = -0.2 if direction == "left" else 1.2
        steps = 10
        delay = 20

        def step(i):
            if i > steps:
                callback()
                return
            relx = start_x + (end_x - start_x) * i / steps
            self.image_label.place_configure(relx=relx)
            self.root.after(delay, lambda: step(i + 1))

        step(0)

    def move_current_file(self, destination_folder):
        filename = self.image_files[self.current_index]
        src = os.path.join(self.folder, filename)
        dst = os.path.join(destination_folder, filename)
        shutil.move(src, dst)
        self.history.append((filename, destination_folder))
        self.current_index += 1
        self.show_image()

    def move_to_yes(self):
        self.animate_swipe("right", lambda: self.move_current_file(self.yes_folder))

    def move_to_no(self):
        self.animate_swipe("left", lambda: self.move_current_file(self.no_folder))

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

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoSorterApp(root)
    root.mainloop()
