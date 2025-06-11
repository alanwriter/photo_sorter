import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from imagededup.methods import CNN
import torch

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')

class PhotoSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📂 照片分類器 Photo Sorter")
        self.root.geometry("1200x850")
        self.root.configure(bg="#1e1e1e")

        self.main_frame = tk.Frame(root, bg="#1e1e1e")
        self.main_frame.pack(expand=True, fill="both")

        self.top_status_frame = tk.Frame(self.main_frame, bg="#2e2e2e")
        self.top_status_frame.place(relx=0.5, rely=0.05, anchor="n")

        self.remaining_label = tk.Label(self.top_status_frame, text="", bg="#2e2e2e", fg="white")
        self.remaining_label.pack(side="left", padx=10)

        self.left_canvas = tk.Canvas(self.main_frame, bg="#1e1e1e", width=160, highlightthickness=0)
        self.left_inner_frame = tk.Frame(self.left_canvas, bg="#1e1e1e")
        self.left_canvas.create_window((0, 0), window=self.left_inner_frame, anchor="nw")
        self.left_canvas.place(relx=0.0, rely=0.5, anchor="w", height=800)

        self.image_label = tk.Label(self.main_frame, bg="#1e1e1e")
        self.image_label.place(relx=0.5, rely=0.5, anchor="center")
        self.image_label.bind("<Button-1>", lambda e: self.move_to_no())
        self.image_label.bind("<Button-3>", lambda e: self.move_to_yes())

        self.similar_canvas = tk.Canvas(self.main_frame, bg="#1e1e1e", width=250, highlightthickness=0)
        self.similar_inner_frame = tk.Frame(self.similar_canvas, bg="#1e1e1e")
        self.similar_canvas.create_window((0, 0), window=self.similar_inner_frame, anchor="nw")
        self.similar_canvas.place(relx=1.0, rely=0.5, anchor="e", height=800, x=160)

        btn_frame = tk.Frame(root, bg="#2e2e2e")
        btn_frame.pack(side="bottom", fill="x", pady=10)
        style = {"bg": "#3e3e3e", "fg": "white", "activebackground": "#5e5e5e", "activeforeground": "white", "width": 20}
        tk.Button(btn_frame, text="🔙 回上一張 (Backspace)", command=self.undo_move, **style).pack(side="left", padx=10, pady=5)
        tk.Button(btn_frame, text="❌ 不喜歡 (左鍵)", command=self.move_to_no, **style).pack(side="left", padx=10, pady=5)
        tk.Button(btn_frame, text="❤️ 喜歡 (右鍵)", command=self.move_to_yes, **style).pack(side="left", padx=10, pady=5)
        tk.Button(btn_frame, text="💎 最愛", command=self.move_to_favorite, **style).pack(side="left", padx=10, pady=5)
        self.rotate_left_btn = tk.Button(btn_frame, text="↺ 左轉", command=self.rotate_left, **style)
        self.rotate_left_btn.pack(side="left", padx=10, pady=5)
        self.rotate_right_btn = tk.Button(btn_frame, text="↻ 右轉", command=self.rotate_right, **style)
        self.rotate_right_btn.pack(side="left", padx=10, pady=5)
        tk.Button(btn_frame, text="🚪 先做到這邊 (Esc)", command=self.exit_program, **style).pack(side="right", padx=10, pady=5)

        self.filename_display = tk.Label(btn_frame, text="", bg="#3e3e3e", fg="white", width=40, relief="groove")
        self.filename_display.pack(side="left", padx=10)

        self.root.bind_all("<Left>", lambda e: self.move_to_no())
        self.root.bind_all("<Right>", lambda e: self.move_to_yes())
        self.root.bind_all("<BackSpace>", lambda e: self.undo_move())
        self.root.bind_all("<Escape>", lambda e: self.exit_program())
        self.root.bind_all("<f>", lambda e: self.move_to_favorite())

        self.folder = ''
        self.image_files = []
        self.current_index = 0
        self.history = []
        self.duplicates = {}
        self.thumbs = {}
        self.thumb_labels = []
        self.rotation_angle = 0

        self.loading_label = tk.Label(self.main_frame, text="正在載入特徵中...", bg="#1e1e1e", fg="white", font=("Arial", 16))
        self.loading_label.place(relx=0.5, rely=0.1, anchor="n")
        self.root.after_idle(self.setup_folder)
        # 左側縮圖欄位
        self.left_canvas = tk.Canvas(self.main_frame, bg="#1e1e1e", width=160, highlightthickness=0, bd=0)
        self.left_inner_frame = tk.Frame(self.left_canvas, bg="#1e1e1e")

        # 放進 canvas 中
        self.left_canvas.create_window((0, 0), window=self.left_inner_frame, anchor="nw")

        # 放到左邊
        self.left_canvas.place(relx=0.0, rely=0.5, anchor="w", height=800)

        # 當縮圖數量變動時自動更新 scroll 區域
        self.left_inner_frame.bind(
            "<Configure>",
            lambda e: self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))
        )
        def bind_scroll_events(canvas):
            canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", lambda ev: canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")))
            canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        bind_scroll_events(self.left_canvas)

    def rotate_left(self):
        self.rotate_and_save(-90)

    def rotate_right(self):
        self.rotate_and_save(90)

    def rotate_and_save(self, angle):
        # 取得目前圖檔路徑
        image_path = os.path.join(self.folder, self.image_files[self.current_index])
        try:
            img = Image.open(image_path)
            rotated = img.rotate(angle, expand=True)
            rotated.save(image_path)  # 覆蓋原圖
            self.rotation_angle = 0   # 清除旋轉狀態
            self.show_image()         # 重新顯示
        except Exception as e:
            print("旋轉失敗:", e)
            messagebox.showerror("錯誤", f"無法旋轉圖片：{e}")

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
        self.favorite_folder = os.path.join(folder, "Favorite")
        os.makedirs(self.yes_folder, exist_ok=True)
        os.makedirs(self.no_folder, exist_ok=True)
        os.makedirs(self.favorite_folder, exist_ok=True)

        self.image_files = [f for f in os.listdir(folder) if f.lower().endswith(SUPPORTED_FORMATS)]
        if not self.image_files:
            messagebox.showinfo("提示", "找不到圖片檔案")
            self.root.quit()
            return

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        cnn = CNN()
        cnn.model.to(device)

        def background():
            self.encodings = cnn.encode_images(image_dir=self.folder)
            self.duplicates = cnn.find_duplicates(encoding_map=self.encodings, min_similarity_threshold=0.9, scores=True)
            self.root.after(0, self.after_encoding_done)
        threading.Thread(target=background, daemon=True).start()

    def after_encoding_done(self):
        self.loading_label.destroy()
        for i, fname in enumerate(self.image_files):
            path = os.path.join(self.folder, fname)
            try:
                img = Image.open(path)
                img.thumbnail((80, 80))
                thumb = ImageTk.PhotoImage(img)
                lbl = tk.Label(self.left_inner_frame, image=thumb, bg="#1e1e1e")
                lbl.image = thumb
                lbl.pack(pady=4)
                lbl.bind("<Button-1>", lambda e, idx=i: self.jump_to_index(idx))
                self.thumb_labels.append(lbl)
                self.thumbs[fname] = thumb
            except: continue
        self.show_image()

    def show_image(self):
        if self.current_index >= len(self.image_files):
            messagebox.showinfo("完成", "所有圖片已分類完成！")
            self.root.quit()
            return
        path = os.path.join(self.folder, self.image_files[self.current_index])
        img = Image.open(path)
        img = img.rotate(self.rotation_angle, expand=True)
        img.thumbnail((900, 700))
        self.tk_img = ImageTk.PhotoImage(img)
        self.image_label.config(image=self.tk_img)
        self.filename_display.config(text=self.image_files[self.current_index])
        self.remaining_label.config(text=f"剩餘 {len(self.image_files) - self.current_index} 張")
        for i, lbl in enumerate(self.thumb_labels):
            lbl.config(bg="white" if i == self.current_index else "#1e1e1e")
        self.left_canvas.yview_moveto(max(0, self.current_index / len(self.image_files)))
        self.show_similar_images(self.image_files[self.current_index])

    def show_similar_images(self, current_filename):
        for widget in self.similar_inner_frame.winfo_children():
            widget.destroy()
        if current_filename not in self.duplicates:
            return
        for fname, _ in sorted(self.duplicates[current_filename], key=lambda x: -x[1]):
            try:
                img = Image.open(os.path.join(self.folder, fname))
                img.thumbnail((80, 80))
                thumb = ImageTk.PhotoImage(img)
                lbl = tk.Label(self.similar_inner_frame, image=thumb, bg="#1e1e1e")
                lbl.image = thumb
                lbl.pack(pady=4)
                lbl.bind("<Button-1>", lambda e, f=fname: self.jump_to_image(f))
            except: continue

    def jump_to_image(self, filename):
        if filename in self.image_files:
            self.current_index = self.image_files.index(filename)
            self.show_image()

    def jump_to_index(self, index):
        if 0 <= index < len(self.image_files):
            self.current_index = index
            self.show_image()

    def move_current_file(self, dest):
        fname = self.image_files[self.current_index]
        shutil.move(os.path.join(self.folder, fname), os.path.join(dest, fname))
        self.history.append((fname, dest))
        self.current_index += 1
        self.rotation_angle = 0
        self.show_image()

    def move_to_yes(self):
        self.move_current_file(self.yes_folder)

    def move_to_no(self):
        self.move_current_file(self.no_folder)

    def move_to_favorite(self):
        self.move_current_file(self.favorite_folder)

    def undo_move(self):
        if not self.history: return
        fname, folder = self.history.pop()
        shutil.move(os.path.join(folder, fname), os.path.join(self.folder, fname))
        self.current_index -= 1
        self.show_image()

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoSorterApp(root)
    root.mainloop()
