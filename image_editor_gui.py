#!/usr/bin/env python3
# Valós idejű előnézetes képszerkesztő (batch)
# Kicsinyítés, forgatás, kivágás — élő preview + egérrel húzható crop

import os
from pathlib import Path
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog

class ImageEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Képszerkesztő (Batch)")
        self.root.geometry("1200x700")

        self.current_image = None
        self.original_image = None
        self.image_paths = []

        # Crop rajzolás változók
        self.start_x = None
        self.start_y = None
        self.crop_rect = None

        # ---- Bal oldali panel ----
        left_frame = tk.Frame(root)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        tk.Button(left_frame, text="Mappa kiválasztása", command=self.select_folder).pack()
        self.listbox = tk.Listbox(left_frame, width=40)
        self.listbox.pack(fill=tk.Y, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.load_selected_image)

        # ---- Jobb oldali preview és vezérlők ----
        right_frame = tk.Frame(root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Canvas kell a crop téglalap rajzolás miatt
        self.preview_canvas = tk.Canvas(right_frame, bg="gray")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Egérkezelők
        self.preview_canvas.bind("<Button-1>", self.start_crop)
        self.preview_canvas.bind("<B1-Motion>", self.draw_crop)
        self.preview_canvas.bind("<ButtonRelease-1>", self.end_crop)

        controls = tk.Frame(right_frame)
        controls.pack(pady=10)

        tk.Label(controls, text="Új méret (sz×m):").grid(row=0, column=0, sticky=tk.W)
        self.resize_entry = tk.Entry(controls)
        self.resize_entry.grid(row=0, column=1)
        self.resize_entry.bind("<KeyRelease>", self.update_preview)

        tk.Label(controls, text="Forgatás (fok):").grid(row=1, column=0, sticky=tk.W)
        self.rotate_entry = tk.Entry(controls)
        self.rotate_entry.grid(row=1, column=1)
        self.rotate_entry.bind("<KeyRelease>", self.update_preview)

        tk.Label(controls, text="Kivágás (x1,y1,x2,y2):").grid(row=2, column=0, sticky=tk.W)
        self.crop_entry = tk.Entry(controls)
        self.crop_entry.grid(row=2, column=1)
        self.crop_entry.bind("<KeyRelease>", self.update_preview)

        self.save_button = tk.Button(
            right_frame,
            text="Mentés minden képre",
            bg="#b6ffb6",
            command=self.save_all
        )
        self.save_button.pack(fill=tk.X, padx=20, pady=10)

    # ----------------------
    # BETÖLTÉS
    # ----------------------

    def select_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.image_paths = [
            str(Path(folder) / f)
            for f in os.listdir(folder)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp"))
        ]

        self.listbox.delete(0, tk.END)
        for path in self.image_paths:
            self.listbox.insert(tk.END, os.path.basename(path))

    def load_selected_image(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return

        idx = sel[0]
        img_path = self.image_paths[idx]

        self.original_image = Image.open(img_path).convert("RGB")
        self.current_image = self.original_image.copy()

        self.update_preview()

    # ----------------------
    # SZERKESZTÉSI FUNKCIÓK
    # ----------------------

    def apply_edits(self, img):
        edited = img.copy()

        # --- Átméretezés ---
        size_text = self.resize_entry.get().strip()
        if "x" in size_text.lower():
            try:
                w, h = map(int, size_text.lower().split("x"))
                edited = edited.resize((w, h), Image.LANCZOS)
            except:
                pass

        # --- Forgatás ---
        rot = self.rotate_entry.get().strip()
        try:
            if rot:
                edited = edited.rotate(-int(rot), expand=True)
        except:
            pass

        # --- Kivágás (x1,y1,x2,y2) ---
        crop_vals = self.crop_entry.get().replace(",", " ").split()
        if len(crop_vals) == 4:
            try:
                x1, y1, x2, y2 = map(int, crop_vals)
                if x2 < x1: x1, x2 = x2, x1
                if y2 < y1: y1, y2 = y2, y1
                edited = edited.crop((x1, y1, x2, y2))
            except:
                pass

        return edited

    # ----------------------
    # ELŐNÉZET
    # ----------------------

    def update_preview(self, event=None):
        if self.original_image is None:
            return

        edited = self.apply_edits(self.original_image)
        self.current_image = edited

        preview = edited.copy()

        # Canvas méret
        canvas_w = self.preview_canvas.winfo_width()
        canvas_h = self.preview_canvas.winfo_height()

        if canvas_w < 50: canvas_w = 600
        if canvas_h < 50: canvas_h = 600

        preview.thumbnail((canvas_w, canvas_h))

        self.preview_image_tk = ImageTk.PhotoImage(preview)

        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, anchor="nw", image=self.preview_image_tk)

    # ----------------------
    # CROP – egérrel
    # ----------------------

    def start_crop(self, event):
        self.start_x = event.x
        self.start_y = event.y

        if self.crop_rect:
            self.preview_canvas.delete(self.crop_rect)
            self.crop_rect = None

    def draw_crop(self, event):
        if self.crop_rect:
            self.preview_canvas.delete(self.crop_rect)

        self.crop_rect = self.preview_canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="red", width=2
        )

    def end_crop(self, event):
        if self.current_image is None:
            return

        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y

        if x2 < x1: x1, x2 = x2, x1
        if y2 < y1: y1, y2 = y2, y1

        pw = self.preview_image_tk.width()
        ph = self.preview_image_tk.height()
        iw = self.current_image.width
        ih = self.current_image.height

        scale_x = iw / pw
        scale_y = ih / ph

        real_x1 = int(x1 * scale_x)
        real_y1 = int(y1 * scale_y)
        real_x2 = int(x2 * scale_x)
        real_y2 = int(y2 * scale_y)

        self.crop_entry.delete(0, tk.END)
        self.crop_entry.insert(0, f"{real_x1} {real_y1} {real_x2} {real_y2}")

        self.update_preview()

    # ----------------------
    # MENTÉS
    # ----------------------

    def save_all(self):
        if not self.image_paths:
            return

        outdir = Path("output_images")
        outdir.mkdir(exist_ok=True)

        for path in self.image_paths:
            img = Image.open(path).convert("RGB")
            edited = self.apply_edits(img)
            save_path = outdir / (Path(path).stem + "_edited.jpg")
            edited.save(save_path)

        print("Mentés kész!")

# ----------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageEditor(root)
    root.mainloop()
