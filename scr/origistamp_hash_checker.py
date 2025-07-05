import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import hashlib, os, pyperclip, datetime, zipfile
from PIL import Image
import imagehash
import json
import webbrowser
import markdown2
from weasyprint import HTML

SUPPORTED_FORMATS = (
    '.txt', '.md', '.pdf', '.docx', '.odt', '.rtf',
    '.json', '.csv', '.xml', '.yaml', '.yml', '.ini',
    '.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.sh', '.bat', '.ts',
    '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.ico', '.psd',
    '.exe', '.msi', '.dll', '.so', '.app', '.dmg', '.deb', '.rpm'
)

CONFIG_FILE = "config.json"

def get_image_hash(filepath):
    try:
        img = Image.open(filepath)
        phash = imagehash.phash(img)
        return str(phash)
    except Exception as e:
        print(f"[!] Image hash failed: {e}")
        return "-"


class DocHashApp:
    def __init__(self, root):
        self.root = root
        self.root.title("\U0001f522 Origistamp Hash - File Hashing & Verification Tool")
        self.root.geometry("820x750")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.file_paths = []
        self.hash_results = {}
        self.sha_report_text = ""
        self.comparison_result_text = ""
        self.open_folder_var = tk.BooleanVar(value=False)

        self.build_ui()
        self.load_config()

    def build_ui(self):
        donate_frame = ctk.CTkFrame(self.root)
        donate_frame.pack(fill="x", padx=20, pady=(10, 0))

        donate_label = ctk.CTkLabel(donate_frame, text=" ☕ ", text_color="#00B9FE", cursor="hand2")
        donate_label.pack(side="right")
        donate_label.bind("<Button-1>", lambda e: self.open_url("https://ko-fi.com/sfs")) 
        
        frame = ctk.CTkFrame(self.root, corner_radius=15)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.label_path = ctk.CTkLabel(frame, text="\U0001f4c2 Selected Files: None", anchor="w")
        self.label_path.pack(fill="x", pady=2)

        self.label_sha = ctk.CTkLabel(frame, text="\U0001f522 SHA-256: -", anchor="w")
        self.label_sha.pack(fill="x", pady=2)

        self.label_status = ctk.CTkLabel(frame, text="\U0001f4ac Status: Waiting", anchor="w")
        self.label_status.pack(fill="x", pady=2)

        self.author_entry = ctk.CTkEntry(frame, placeholder_text="Author / Creator Name (optional)")
        self.author_entry.pack(fill="x", padx=10, pady=(5, 2))

        self.note_entry = ctk.CTkEntry(frame, placeholder_text="Note / Version Info (optional)")
        self.note_entry.pack(fill="x", padx=10, pady=(2, 10))
        
        self.gpg_entry = ctk.CTkEntry(frame, placeholder_text="GPG Fingerprint (optional, 40 hex chars)")
        self.gpg_entry.pack(fill="x", padx=10, pady=(2, 10))


        self.progress = ctk.CTkProgressBar(frame)
        self.progress.pack(fill="x", pady=10)
        self.progress.set(0)

        btns = ctk.CTkFrame(frame)
        btns.pack(fill="x", pady=5)

        ctk.CTkButton(btns, text="\U0001f4c1 Select Files", command=self.select_files).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="\U0001f4c2 Select Folder", command=self.select_folder).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="\U0001f50d Compare Two Files", command=self.compare_files_popup).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="\U0001f5bc Compare Two Images", command=self.compare_images_popup).pack(side="left", padx=5)

        self.tree = ttk.Treeview(frame, columns=("filename", "sha256", "size", "created", "modified", "img_hash"), show="headings", height=10)

        self.tree.heading("filename", text="File Name")
        self.tree.heading("sha256", text="SHA-256")
        self.tree.heading("size", text="Size")
        self.tree.heading("img_hash", text="Image Hash")

        self.tree.pack(fill="both", pady=10)

        option_row = ctk.CTkFrame(frame)
        option_row.pack(fill="x", padx=10, pady=(5, 10))

        checkbox_open_folder = ctk.CTkCheckBox(
        option_row, text="Open folder after saving report", variable=self.open_folder_var)
        checkbox_open_folder.pack(side="left", padx=5)

        format_frame = ctk.CTkFrame(option_row, fg_color="transparent") 
        format_frame.pack(side="right", padx=5)

        ctk.CTkLabel(format_frame, text="Format:").pack(side="left", padx=(5, 5))
        self.export_format_var = tk.StringVar(value="md")
        format_menu = ctk.CTkOptionMenu(format_frame, variable=self.export_format_var, values=["md", "pdf", "both"])
        format_menu.pack(side="left", padx=(0, 5))

        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="\U0001f4cb Copy SHA Report", command=self.copy_sha_report).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="\U0001f4be Save Report", command=self.save_report).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="\U0001f4e6 Create ZIP", command=self.create_zip).pack(side="left", padx=5)

    def open_url(self, url):
        webbrowser.open(url)  
        
    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)

            self.author_entry.insert(0, config.get("author", ""))
            self.note_entry.insert(0, config.get("note", ""))
            self.gpg_entry.insert(0, config.get("gpg", ""))

            self.open_folder_var.set(config.get("open_folder", False))
            self.export_format_var.set(config.get("export_format", "md"))

        except Exception as e:
            print(f"[!] Failed to load config: {e}")

    def save_config(self):
        config_data = {
            "open_folder": self.open_folder_var.get(),
            "author": self.author_entry.get().strip(),
            "note": self.note_entry.get().strip(),
            "gpg": self.gpg_entry.get().strip(),
            "export_format": self.export_format_var.get()
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"[!] Failed to save config: {e}")
    
    def convert_markdown_to_pdf(self, md_text, output_path):
        html = markdown2.markdown(md_text, extras=["fenced-code-blocks", "tables", "strike", "cuddled-lists"])

        html_doc = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{
                    size: A4 landscape;
                    margin: 1in;
                }}
                body {{
                    font-family: 'Segoe UI', sans-serif;
                    margin: 0;
                    line-height: 1.5;
                    font-size: 12px;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    table-layout: fixed;
                    word-wrap: break-word;
                    font-size: 10px;
                }}
                th, td {{
                    border: 1px solid #ccc;
                    padding: 6px;
                    text-align: left;
                    vertical-align: top;
                    word-break: break-word;
                    overflow-wrap: break-word;
                }}
                code {{
                    background-color: #f2f2f2;
                    padding: 2px 4px;
                    border-radius: 4px;
                    font-family: Consolas, monospace;
                    font-size: 9px;
                    word-break: break-all;
                }}
                pre code {{
                    background-color: #f6f6f6;
                    display: block;
                    padding: 1em;
                    overflow-x: auto;
                    white-space: pre-wrap;
                    word-break: break-word;
                }}
                h1, h2, h3 {{
                    margin-top: 1em;
                    margin-bottom: 0.5em;
                }}
            </style>
        </head>
        <body>{html}</body>
        </html>
        """

        HTML(string=html_doc).write_pdf(output_path)

    def compare_images_popup(self):
        f1 = filedialog.askopenfilename(title="Select First Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp;*.tiff")])
        if not f1:
            return
        f2 = filedialog.askopenfilename(title="Select Second Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp;*.tiff")])
        if not f2:
            return

        try:
            hash1 = imagehash.phash(Image.open(f1))
            hash2 = imagehash.phash(Image.open(f2))
            diff = abs(hash1 - hash2)
            result = f"❗ pHash difference: {diff} — {'Highly Similar' if diff <= 5 else 'Different'}"
        except Exception as e:
            messagebox.showerror("Error", f"Image hash failed: {e}")
            return

        popup = tk.Toplevel(self.root)
        popup.title("Compare Images")
        popup.geometry("700x300")

        tk.Label(popup, text=f"Image A: {os.path.basename(f1)}\nHash: {hash1}", anchor="w").pack(fill="x", padx=10, pady=5)
        tk.Label(popup, text=f"Image B: {os.path.basename(f2)}\nHash: {hash2}", anchor="w").pack(fill="x", padx=10, pady=5)
        tk.Label(popup, text=result, font=("Arial", 12, "bold")).pack(pady=10)

        def copy_result():
            pyperclip.copy(f"Image A: {hash1}\nImage B: {hash2}\nDifference: {diff}\nResult: {result}")
            messagebox.showinfo("Copied", "Comparison result copied to clipboard.")

        ctk.CTkButton(popup, text="\U0001f4cb Copy Result", command=copy_result).pack(pady=10)


    def select_files(self):
        selected = filedialog.askopenfilenames(title="Select Documents", filetypes=[("Supported Files", "*.*")])
        if selected:
            self.load_files(selected)

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            collected = []
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(SUPPORTED_FORMATS):
                        collected.append(os.path.join(root, file))
            self.load_files(collected)

    def load_files(self, paths):
        self.file_paths = [p for p in paths if p.lower().endswith(SUPPORTED_FORMATS)]
        self.hash_results.clear()
        self.tree.delete(*self.tree.get_children())

        if not self.file_paths:
            self.label_status.configure(text="⚠️ No supported files found.")
            return

        self.label_path.configure(text=f"\U0001f4c2 Selected Files: {len(self.file_paths)}")
        self.label_sha.configure(text="\U0001f522 SHA-256: Processing...")
        self.label_status.configure(text="\U0001f4ac Calculating hashes...")

        self.progress.set(0)

        self.sha_report_text = "| File Name | SHA-256 | Size |\n"
        self.sha_report_text += "|-----------|---------|------|\n"

        for i, f in enumerate(self.file_paths):
            try:
                with open(f, 'rb') as file:
                    file_data = file.read()
                    sha = hashlib.sha256(file_data).hexdigest()

                stat = os.stat(f)
                
                size_kb = f"{stat.st_size / 1024:.2f} KB"

                self.hash_results[f] = {
                    "sha": sha,
                    "size": size_kb,
                }

                info = self.hash_results[f]
                self.tree.insert('', 'end', values=(os.path.basename(f), info["sha"], info["size"]))

                self.sha_report_text += f"| {os.path.basename(f)} | `{sha}` | {size_kb} |\n"

            except Exception as e:
                print(f"[!] Error processing {f}: {e}")

            self.progress.set((i + 1) / len(self.file_paths))

        self.label_sha.configure(text="\U0001f522 SHA-256: Done")
        self.label_status.configure(text=f"✅ Hashed {len(self.file_paths)} file(s).")


    def copy_sha_report(self):
        if not self.sha_report_text.strip():
            messagebox.showinfo("Nothing to Copy", "Please hash some files first.")
            return
        try:
            author = self.author_entry.get().strip()
            note = self.note_entry.get().strip()
            gpg_fp = self.gpg_entry.get().strip()
            if gpg_fp:
                if len(gpg_fp) != 40 or not all(c in "0123456789abcdefABCDEF" for c in gpg_fp):
                    messagebox.showerror("Invalid GPG Fingerprint", "GPG fingerprint must be exactly 40 hexadecimal characters.")
                return

            metadata = ""
            if author:
                metadata += f"**Author:** {author}\n"
            if note:
                metadata += f"**Notes:** {note}\n"
            if gpg_fp:
                metadata += f"**GPG Fingerprint:** `{gpg_fp}`\n"
    
            metadata += f"**Report Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

            full_text = "# SHA-256 Hash Report\n\n" + metadata + "\n\n" + self.sha_report_text

            if self.comparison_result_text:
                full_text += "\n\n" + self.comparison_result_text

            pyperclip.copy(full_text)
            self.label_status.configure(text="\U0001f4cb SHA copied to clipboard")
        except Exception as e:
            self.label_status.configure(text=f"❌ Copy failed: {e}")


    def save_report(self):
        if not self.file_paths and not self.comparison_result_text:
            messagebox.showwarning("No Data", "Generate some hashes or comparison first.")
            return

        filename = f"SHA_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        export_mode = self.export_format_var.get()
        default_ext = ".md" if export_mode == "md" else ".pdf"
        filetypes = [("Markdown Files", "*.md")] if export_mode == "md" else [("PDF Files", "*.pdf")]

        if export_mode == "both":
            default_ext = ".md"
            filetypes = [("Markdown Files", "*.md"), ("PDF Files", "*.pdf"), ("All Files", "*.*")]

        filename = f"SHA_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        path = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            initialfile=filename,
            filetypes=filetypes
        )

        if not path:
            return

        try:
            author = self.author_entry.get().strip()
            note = self.note_entry.get().strip()
            gpg_fp = self.gpg_entry.get().strip()

            if gpg_fp and (len(gpg_fp) != 40 or not all(c in "0123456789abcdefABCDEF" for c in gpg_fp)):
                messagebox.showerror("Invalid GPG Fingerprint", "GPG fingerprint must be exactly 40 hexadecimal characters.")
                return

            metadata = ""
            if author:
                metadata += f"**Author:** {author}\n"
            if note:
                metadata += f"**Notes:** {note}\n"
            if gpg_fp:
                metadata += f"**GPG Fingerprint:** `{gpg_fp}`\n"
            metadata += f"**Report Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

            content = "# SHA-256 Hash Report\n\n" + metadata + "\n\n" + self.sha_report_text
            if self.comparison_result_text:
                content += "\n\n" + self.comparison_result_text

            export_mode = self.export_format_var.get()
            base_filename = os.path.splitext(os.path.basename(path))[0]
            save_dir = os.path.dirname(path)

            if export_mode in ["md", "both"]:
                md_path = os.path.join(save_dir, base_filename + ".md")
                with open(md_path, 'w', encoding='utf-8-sig') as f:
                    f.write(content)

            if export_mode in ["pdf", "both"]:
                pdf_path = os.path.join(save_dir, base_filename + ".pdf")
                self.convert_markdown_to_pdf(content, pdf_path)

            if self.open_folder_var.get():
                folder = save_dir
                try:
                    if os.name == 'nt':
                        os.startfile(folder)
                    elif os.name == 'posix':
                        import subprocess
                        subprocess.run(['xdg-open', folder])
                except Exception as e:
                    print(f"[!] Folder open error: {e}")

            self.label_status.configure(text=f"\U0001f4be Report saved as: {export_mode.upper()}")
        except Exception as e:
            self.label_status.configure(text=f"❌ Save failed: {e}")



    def create_zip(self):
        if not self.file_paths:
            messagebox.showwarning("No Files", "Hash some files first.")
            return

        default_name = f"DocHash_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = filedialog.asksaveasfilename(defaultextension=".zip", initialfile=default_name, filetypes=[("ZIP Archives", "*.zip")])
        if not zip_path:
            return

        try:
            export_mode = self.export_format_var.get()
            base_filename = "sha_report"
            temp_dir = os.path.dirname(zip_path)
            md_path = os.path.join(temp_dir, base_filename + ".md")
            pdf_path = os.path.join(temp_dir, base_filename + ".pdf")

            author = self.author_entry.get().strip()
            note = self.note_entry.get().strip()
            gpg_fp = self.gpg_entry.get().strip()

            if gpg_fp and (len(gpg_fp) != 40 or not all(c in "0123456789abcdefABCDEF" for c in gpg_fp)):
                messagebox.showerror("Invalid GPG Fingerprint", "GPG fingerprint must be exactly 40 hexadecimal characters.")
                return

            metadata = ""
            if author:
                metadata += f"**Author:** {author}\n"
            if note:
                metadata += f"**Notes:** {note}\n"
            if gpg_fp:
                metadata += f"**GPG Fingerprint:** `{gpg_fp}`\n"
            metadata += f"**Report Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

            content = "# SHA-256 Hash Report\n\n" + metadata + "\n\n" + self.sha_report_text
            if self.comparison_result_text:
                content += "\n\n" + self.comparison_result_text

            if export_mode in ["md", "both"]:
                with open(md_path, 'w', encoding='utf-8-sig') as f:
                    f.write(content)

            if export_mode in ["pdf", "both"]:
                self.convert_markdown_to_pdf(content, pdf_path)

            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for path in self.file_paths:
                    zipf.write(path, os.path.basename(path))
                if export_mode in ["md", "both"]:
                    zipf.write(md_path, os.path.basename(md_path))
                if export_mode in ["pdf", "both"]:
                    zipf.write(pdf_path, os.path.basename(pdf_path))
                    
            try:
                with open(zip_path, "rb") as zf:
                    zip_hash = hashlib.sha256(zf.read()).hexdigest()
                    sha256_path = zip_path + ".sha256"
                with open(sha256_path, "w", encoding="utf-8") as sha_file:
                    sha_file.write(f"{zip_hash}  {os.path.basename(zip_path)}\n")
            except Exception as e:
                print(f"[!] Failed to write SHA256 file: {e}")        

            if os.path.exists(md_path):
                os.remove(md_path)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

            if self.open_folder_var.get():
                folder = os.path.dirname(zip_path)
                try:
                    if os.name == 'nt':
                        os.startfile(folder)
                    elif os.name == 'posix':
                        import subprocess
                        subprocess.run(['xdg-open', folder])
                except Exception as e:
                    print(f"[!] Folder open error: {e}")

            self.label_status.configure(text=f"\U0001f4e6 ZIP created → {os.path.basename(zip_path)}")
        except Exception as e:
            self.label_status.configure(text=f"❌ ZIP failed: {e}")


    def compare_files_popup(self):
        f1 = filedialog.askopenfilename(title="Select First File", filetypes=[("All Files", "*.*")])
        if not f1:
            return
        f2 = filedialog.askopenfilename(title="Select Second File", filetypes=[("All Files", "*.*")])
        if not f2:
            return

        try:
            with open(f1, 'rb') as a:
                hash1 = hashlib.sha256(a.read()).hexdigest()
            with open(f2, 'rb') as b:
                hash2 = hashlib.sha256(b.read()).hexdigest()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read files: {e}")
            return

        result = "✅ Files are IDENTICAL." if hash1 == hash2 else "❌ Files are DIFFERENT."
        self.comparison_result_text = f"# File Comparison\n\n- File A: `{os.path.basename(f1)}`\n  - SHA-256: `{hash1}`\n- File B: `{os.path.basename(f2)}`\n  - SHA-256: `{hash2}`\n\n**Result:** {result}"

        popup = tk.Toplevel(self.root)
        popup.title("Compare Files")
        popup.geometry("700x300")

        tk.Label(popup, text=f"File A: {os.path.basename(f1)}", anchor="w").pack(fill="x", padx=10, pady=2)
        tk.Label(popup, text=f"SHA-256: {hash1}", anchor="w", wraplength=680).pack(fill="x", padx=10, pady=2)

        tk.Label(popup, text=f"\nFile B: {os.path.basename(f2)}", anchor="w").pack(fill="x", padx=10, pady=2)
        tk.Label(popup, text=f"SHA-256: {hash2}", anchor="w", wraplength=680).pack(fill="x", padx=10, pady=2)

        tk.Label(popup, text=f"\n{result}", anchor="center", font=("Arial", 12, "bold")).pack(pady=10)

        def copy_result():
            pyperclip.copy(self.comparison_result_text)
            messagebox.showinfo("Copied", "Comparison result copied to clipboard.")

        ctk.CTkButton(popup, text="\U0001f4cb Copy Result", command=copy_result).pack(pady=10)


if __name__ == '__main__':
    root = ctk.CTk()
    app = DocHashApp(root)
    
    def on_close():
        app.save_config()
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_close)    
    root.mainloop()
