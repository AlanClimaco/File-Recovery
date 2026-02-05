import os
import sys
import ctypes
import threading
import io
import hashlib
import time
import math
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageFile, ImageDraw 
import customtkinter as ctk

# Permite carregar imagens truncadas
ImageFile.LOAD_TRUNCATED_IMAGES = True

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Configuração de ID para ícone na barra de tarefas
try:
    myappid = 'alab.recovery.tool.v3'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass

# Função para localizar arquivos dentro do executável
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

TRANSLATIONS = {
    "pt": {
        "title": "Alab Recovery Tool",
        "sidebar_title": "ALAB TOOLS",
        "lbl_lang_title": "Idioma / Language:",
        "lbl_drive": "Selecione o Drive:",
        "lbl_filters": "Filtros de Arquivo:",
        "lbl_search_title": "Filtrar Conteúdo (Opcional):",
        "lbl_order": "Ordem de Varredura:",
        "lbl_sort": "Organizar Galeria:",
        "chk_junk": "Ignorar Ícones (< 300px)",
        "btn_start": "INICIAR VARREDURA",
        "btn_pause": "PAUSAR",
        "btn_resume": "CONTINUAR",
        "btn_stop": "PARAR",
        "preview_title": "VISUALIZADOR",
        "no_preview": "Clique em um arquivo para ver",
        "btn_save": "SALVAR ARQUIVO",
        "status_ready": "Pronto para recuperar",
        "status_scanning": "Recuperando...",
        "status_paused": "EM PAUSA",
        "combo_all": "Tudo (Imagens, Vídeos, Docs)",
        "combo_img": "Apenas Imagens",
        "combo_vid": "Apenas Vídeos",
        "combo_doc": "Apenas Documentos/Dados",
        "order_start": "Do Início para o Fim",
        "order_end": "Do Fim para o Início",
        "sort_recent": "Recentes (Padrão)",
        "sort_type": "Agrupar por Tipo",
        "sort_size": "Tamanho (Maior primeiro)",
        "ph_keyword": "Ex: 'senha', 'recibo'...",
        "gallery_label": "Arquivos Recuperados",
        "opt_pt": "Português (BR)",
        "opt_en": "English (US)"
    },
    "en": {
        "title": "Alab Recovery Tool",
        "sidebar_title": "ALAB TOOLS",
        "lbl_lang_title": "Language / Idioma:",
        "lbl_drive": "Select Drive:",
        "lbl_filters": "File Filters:",
        "lbl_search_title": "Content Filter (Optional):",
        "lbl_order": "Scan Direction:",
        "lbl_sort": "Sort Gallery:",
        "chk_junk": "Ignore Icons (< 300px)",
        "btn_start": "START SCAN",
        "btn_pause": "PAUSE",
        "btn_resume": "RESUME",
        "btn_stop": "STOP",
        "preview_title": "PREVIEWER",
        "no_preview": "Click a file to preview",
        "btn_save": "SAVE FILE",
        "status_ready": "Ready to recover",
        "status_scanning": "Recovering...",
        "status_paused": "PAUSED",
        "combo_all": "Everything (Img, Vid, Doc)",
        "combo_img": "Images Only",
        "combo_vid": "Videos Only",
        "combo_doc": "Documents/Data Only",
        "order_start": "Start to End",
        "order_end": "End to Start",
        "sort_recent": "Recent (Default)",
        "sort_type": "Group by Type",
        "sort_size": "Size (Largest first)",
        "ph_keyword": "e.g. 'password', 'invoice'...",
        "gallery_label": "Recovered Files",
        "opt_pt": "Portuguese (BR)",
        "opt_en": "English (US)"
    }
}

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

class AlabRecoveryTool(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuração inicial
        self.lang = "pt"
        self.title(TRANSLATIONS[self.lang]["title"])
        self.geometry("1400x900")
        
        # Carrega ícone da janela (.ico)
        try:
            icon_path = resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except: pass
        
        # Dados e estados
        self.all_found_files = []   
        self.display_files = []     
        self.seen_hashes = set()
        self.is_scanning = False
        self.is_paused = False
        self.selected_item = None
        self.target_drive_path = ""
        
        # Paginação
        self.items_per_page = 40
        self.current_page = 0
        self.total_pages = 0
        self.page_images_cache = [] 
        self.last_width = 0
        self.last_height = 0

        # Assinaturas de arquivos
        self.signatures = {
            "JPG":  {"start": b'\xff\xd8\xff', "end": b'\xff\xd9', "ext": ".jpg", "cat": "IMG", "max": 15},
            "PNG":  {"start": b'\x89\x50\x4e\x47', "end": b'\x49\x45\x4e\x44\xae\x42\x60\x82', "ext": ".png", "cat": "IMG", "max": 15},
            "PDF":  {"start": b'%PDF-', "end": b'%%EOF', "ext": ".pdf", "cat": "DOC", "max": 50},
            "JSON": {"start": b'{', "end": b'}', "ext": ".json", "cat": "DADOS", "max": 10},
            "MP4":  {"start": b'ftyp', "end": None, "ext": ".mp4", "cat": "VID", "max": 200},
        }

        self.setup_ui()
        self.update_texts()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === Sidebar ===
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # --- CABEÇALHO (MII + TÍTULO) ---
        self.header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.header_frame.pack(pady=(30, 20), padx=10)

        # Carrega e redimensiona a imagem do Mii (PNG)
        try:
            img_file = resource_path("icon.png") # Busca icon.png
            if os.path.exists(img_file):
                pil_img = Image.open(img_file)
                # Redimensiona para 50x50 para caber na barra
                self.mii_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(55, 55))
                self.lbl_img = ctk.CTkLabel(self.header_frame, text="", image=self.mii_img)
                self.lbl_img.pack(side="left", padx=(0, 10))
        except:
            pass # Se não achar a imagem, só não mostra
        
        self.lbl_sidebar_title = ctk.CTkLabel(self.header_frame, text="ALAB TOOLS", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_sidebar_title.pack(side="left")
        
        # Idioma
        self.lbl_lang_title = ctk.CTkLabel(self.sidebar, text="", anchor="w", font=ctk.CTkFont(weight="bold", size=12))
        self.lbl_lang_title.pack(padx=20, pady=(0, 2), anchor="w")

        self.lang_var = ctk.StringVar()
        self.lang_combo = ctk.CTkComboBox(self.sidebar, variable=self.lang_var, 
                                          width=220, state="readonly", command=self.change_language)
        self.lang_combo.pack(padx=20, pady=(0, 20))

        # Drive
        self.lbl_drive = ctk.CTkLabel(self.sidebar, text="", anchor="w", font=ctk.CTkFont(weight="bold"))
        self.lbl_drive.pack(padx=20, anchor="w")
        
        self.drive_var = ctk.StringVar()
        drives = self.get_physical_drives()
        self.drive_combo = ctk.CTkComboBox(self.sidebar, variable=self.drive_var, values=drives, width=220)
        self.drive_combo.pack(padx=20, pady=5)
        if drives: self.drive_combo.set(drives[0])

        # Filtros
        self.lbl_filters = ctk.CTkLabel(self.sidebar, text="", anchor="w", font=ctk.CTkFont(weight="bold"))
        self.lbl_filters.pack(padx=20, pady=(15, 5), anchor="w")
        
        self.scan_filter_var = ctk.StringVar() 
        self.scan_filter = ctk.CTkComboBox(self.sidebar, state="readonly", width=220)
        self.scan_filter.pack(padx=20, pady=5)
        
        self.lbl_search_title = ctk.CTkLabel(self.sidebar, text="", anchor="w", font=ctk.CTkFont(weight="bold"))
        self.lbl_search_title.pack(padx=20, pady=(15, 5), anchor="w")

        self.keyword_var = ctk.StringVar()
        self.entry_kw = ctk.CTkEntry(self.sidebar, textvariable=self.keyword_var, width=220)
        self.entry_kw.pack(padx=20, pady=5)

        self.ignore_junk_var = ctk.BooleanVar(value=True)
        self.chk_junk = ctk.CTkCheckBox(self.sidebar, variable=self.ignore_junk_var)
        self.chk_junk.pack(padx=20, pady=10, anchor="w")

        # Ordem
        self.lbl_order = ctk.CTkLabel(self.sidebar, text="", anchor="w", font=ctk.CTkFont(weight="bold"))
        self.lbl_order.pack(padx=20, pady=(5, 5), anchor="w")
        
        self.scan_order_combo = ctk.CTkComboBox(self.sidebar, state="readonly", width=220)
        self.scan_order_combo.pack(padx=20, pady=5)

        # Botões de Ação
        self.frame_controls = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.frame_controls.pack(padx=20, pady=20, fill="x")

        self.btn_action = ctk.CTkButton(self.frame_controls, height=50, fg_color="#2ecc71", text_color="black",
                                      font=ctk.CTkFont(weight="bold", size=14), command=self.toggle_scan)
        self.btn_action.pack(side="top", fill="x", expand=True, pady=(0, 10))
        
        self.btn_stop = ctk.CTkButton(self.frame_controls, height=35, fg_color="#e74c3c", width=60, 
                                    state="disabled", command=self.stop_scan)
        self.btn_stop.pack(side="top", fill="x")

        # Organização
        self.lbl_sort = ctk.CTkLabel(self.sidebar, text="", anchor="w", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_sort.pack(pady=(10, 5), padx=20, anchor="w")
        
        self.sort_combo = ctk.CTkComboBox(self.sidebar, state="readonly", width=220, command=self.apply_sorting)
        self.sort_combo.pack(padx=20, pady=5)

        # Status e Progresso
        self.lbl_status = ctk.CTkLabel(self.sidebar, text="", font=("Consolas", 12))
        self.lbl_status.pack(side="bottom", pady=5)
        self.prog_bar = ctk.CTkProgressBar(self.sidebar, height=10, progress_color="#2ecc71")
        self.prog_bar.pack(side="bottom", fill="x", padx=20, pady=(0, 10))
        self.prog_bar.set(0)

        # === Galeria Central ===
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.center_frame.rowconfigure(1, weight=1)
        self.center_frame.columnconfigure(0, weight=1)
        self.center_frame.bind("<Configure>", self.on_resize)

        # Navegação
        self.nav_frame = ctk.CTkFrame(self.center_frame, height=50, fg_color="#232323")
        self.nav_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="<", width=40, command=self.prev_page, state="disabled")
        self.btn_prev.pack(side="left", padx=10)
        
        self.lbl_page = ctk.CTkLabel(self.nav_frame, text="0 / 0", font=("Arial", 14, "bold"))
        self.lbl_page.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(self.nav_frame, text=">", width=40, command=self.next_page, state="disabled")
        self.btn_next.pack(side="right", padx=10)

        self.gallery_area = ctk.CTkScrollableFrame(self.center_frame)
        self.gallery_area.grid(row=1, column=0, sticky="nsew")

        # === Painel de Preview ===
        self.preview_frame = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#181818")
        self.preview_frame.grid(row=0, column=2, sticky="nsew")
        self.preview_frame.grid_propagate(False)

        self.lbl_preview_title = ctk.CTkLabel(self.preview_frame, text="", font=ctk.CTkFont(weight="bold"))
        self.lbl_preview_title.pack(pady=20)
        
        self.lbl_prev_img = ctk.CTkLabel(self.preview_frame, text="", text_color="gray")
        self.lbl_prev_img.pack(expand=True)
        self.current_preview_obj = None 

        self.txt_content = ctk.CTkTextbox(self.preview_frame, height=200, fg_color="#2b2b2b")
        self.txt_content.pack(fill="x", padx=10, pady=10)
        
        self.btn_save = ctk.CTkButton(self.preview_frame, text="", state="disabled", fg_color="#3498db", command=self.save_current)
        self.btn_save.pack(side="bottom", padx=20, pady=20, fill="x")

        self.log_box = ctk.CTkTextbox(self.preview_frame, height=80, font=("Consolas", 10), text_color="#2ecc71", fg_color="black")
        self.log_box.pack(side="bottom", fill="x", padx=10, pady=5)

    def change_language(self, choice):
        is_pt = (choice == TRANSLATIONS["pt"]["opt_pt"]) or ("Português" in choice)
        self.lang = "pt" if is_pt else "en"
        self.update_texts()

    def update_texts(self):
        t = TRANSLATIONS[self.lang]
        
        # Preserva a seleção dos combos
        idx_filter = 0
        if self.scan_filter.get() in self.scan_filter._values:
             idx_filter = self.scan_filter._values.index(self.scan_filter.get())
        
        idx_order = 0
        if self.scan_order_combo.get() in self.scan_order_combo._values:
            idx_order = self.scan_order_combo._values.index(self.scan_order_combo.get())

        idx_sort = 0
        if self.sort_combo.get() in self.sort_combo._values:
            idx_sort = self.sort_combo._values.index(self.sort_combo.get())

        # Atualiza labels
        self.title(t["title"])
        # self.lbl_sidebar_title é estático ("ALAB TOOLS"), não precisa traduzir
        self.lbl_lang_title.configure(text=t["lbl_lang_title"])
        self.lbl_drive.configure(text=t["lbl_drive"])
        self.lbl_filters.configure(text=t["lbl_filters"])
        self.lbl_search_title.configure(text=t["lbl_search_title"])
        self.lbl_order.configure(text=t["lbl_order"])
        self.lbl_sort.configure(text=t["lbl_sort"])
        self.chk_junk.configure(text=t["chk_junk"])
        
        # Atualiza opções
        lang_opts = [t["opt_pt"], t["opt_en"]]
        self.lang_combo.configure(values=lang_opts)
        self.lang_combo.set(t["opt_pt"] if self.lang == "pt" else t["opt_en"])

        filter_vals = [t["combo_all"], t["combo_img"], t["combo_vid"], t["combo_doc"]]
        self.scan_filter.configure(values=filter_vals)
        if idx_filter < len(filter_vals): self.scan_filter.set(filter_vals[idx_filter])
        
        order_vals = [t["order_start"], t["order_end"]]
        self.scan_order_combo.configure(values=order_vals)
        if idx_order < len(order_vals): self.scan_order_combo.set(order_vals[idx_order])
        
        sort_vals = [t["sort_recent"], t["sort_type"], t["sort_size"]]
        self.sort_combo.configure(values=sort_vals)
        if idx_sort < len(sort_vals): self.sort_combo.set(sort_vals[idx_sort])
        
        self.entry_kw.configure(placeholder_text=t["ph_keyword"])
        self.gallery_area.configure(label_text=t["gallery_label"])
        self.lbl_preview_title.configure(text=t["preview_title"])
        self.btn_save.configure(text=t["btn_save"])
        self.btn_stop.configure(text=t["btn_stop"])
        
        if not self.is_scanning:
            self.btn_action.configure(text=t["btn_start"], fg_color="#2ecc71")
            self.lbl_status.configure(text=t["status_ready"])
        elif self.is_paused:
             self.btn_action.configure(text=t["btn_resume"], fg_color="#3498db")
             self.lbl_status.configure(text=t["status_paused"])
        else:
             self.btn_action.configure(text=t["btn_pause"], fg_color="#f39c12")
             self.lbl_status.configure(text=t["status_scanning"])

        if not self.selected_item:
            self.lbl_prev_img.configure(text=t["no_preview"])

    def log(self, msg):
        self.log_box.insert("end", f"> {msg}\n")
        self.log_box.see("end")

    def get_physical_drives(self):
        drives = []
        for i in range(10):
            path = f"PhysicalDrive{i}"
            try:
                with open(f"\\\\.\\{path}", "rb"):
                    drives.append(path)
            except: 
                pass
        if not drives: return ["Nenhum Drive (Admin Req)"]
        return drives

    def on_resize(self, event):
        if abs(event.width - self.last_width) < 50 and abs(event.height - self.last_height) < 50: return
        self.last_width = event.width
        self.last_height = event.height
        
        ITEM_W = 145
        cols = max(1, event.width // ITEM_W)
        rows = max(1, (event.height - 60) // ITEM_W)
        new_per_page = max(1, (cols * rows)) 
        
        if new_per_page != self.items_per_page:
            self.items_per_page = new_per_page
            if self.display_files: self.apply_sorting()

    def toggle_scan(self):
        t = TRANSLATIONS[self.lang]
        if not self.is_scanning:
            val = self.drive_var.get()
            if not val or "Nenhum" in val: return
            
            self.target_drive_path = f"\\\\.\\{val}"
            self.is_scanning, self.is_paused = True, False
            self.all_found_files, self.seen_hashes, self.display_files, self.current_page = [], set(), [], 0
            
            self.scan_filter.configure(state="disabled")
            self.scan_order_combo.configure(state="disabled")
            self.btn_action.configure(text=t["btn_pause"], fg_color="#f39c12") 
            self.btn_stop.configure(state="normal")
            
            threading.Thread(target=self.scan_engine, daemon=True).start()
        
        elif self.is_scanning and not self.is_paused:
            self.is_paused = True
            self.btn_action.configure(text=t["btn_resume"], fg_color="#3498db")
            self.log("PAUSADO.")
            
        elif self.is_scanning and self.is_paused:
            self.is_paused = False
            self.btn_action.configure(text=t["btn_pause"], fg_color="#f39c12")
            self.log("RETOMANDO...")

    def stop_scan(self):
        if self.is_scanning:
            self.is_scanning, self.is_paused = False, False 
            self.log("PARANDO...")

    def scan_engine(self):
        chunk = 1024 * 1024 
        t = TRANSLATIONS[self.lang]
        
        # Mapeamento de filtros
        sel_filter = self.scan_filter.get()
        target_mode = "IMG" 
        if sel_filter in [t["combo_all"], TRANSLATIONS["en"]["combo_all"], TRANSLATIONS["pt"]["combo_all"]]: target_mode = "ALL"
        elif sel_filter in [t["combo_vid"], TRANSLATIONS["en"]["combo_vid"], TRANSLATIONS["pt"]["combo_vid"]]: target_mode = "VID"
        elif sel_filter in [t["combo_doc"], TRANSLATIONS["en"]["combo_doc"], TRANSLATIONS["pt"]["combo_doc"]]: target_mode = "DOC"

        active_signatures = {}
        if target_mode == "ALL": active_signatures = self.signatures
        elif target_mode == "IMG": active_signatures = {k: v for k, v in self.signatures.items() if v["cat"] == "IMG"}
        elif target_mode == "VID": active_signatures = {k: v for k, v in self.signatures.items() if v["cat"] == "VID"}
        else: active_signatures = {k: v for k, v in self.signatures.items() if v["cat"] in ["DOC", "DADOS"]}
        
        keyword = self.keyword_var.get()
        keyword_bytes = keyword.encode('utf-8') if keyword else None
        
        order_mode = self.scan_order_combo.get()
        is_reverse = (order_mode in [t["order_end"], TRANSLATIONS["en"]["order_end"], TRANSLATIONS["pt"]["order_end"]])
        
        self.after(0, lambda: self.log(f"Alab Scanner em: {self.target_drive_path}"))

        try:
            with open(self.target_drive_path, "rb", buffering=0) as disk:
                try: disk.seek(0, 2); total = disk.tell(); disk.seek(0)
                except: total = 500 * (1024**3) 
                
                offset = total - chunk if is_reverse else 0
                step = -chunk if is_reverse else chunk
                last_ui_update = time.time()
                
                while self.is_scanning:
                    if is_reverse and offset < 0: break
                    if not is_reverse and offset >= total: break

                    while self.is_paused and self.is_scanning:
                        time.sleep(0.5) 
                        self.after(0, lambda: self.lbl_status.configure(text=t["status_paused"]))
                    
                    if not self.is_scanning: break 

                    try:
                        disk.seek(offset)
                        data = disk.read(chunk)
                    except: 
                        offset += step
                        continue
                    if not data: break

                    for fmt, sig in active_signatures.items():
                        if sig["start"] in data:
                            start_idx = data.find(sig["start"])
                            raw = data[start_idx:]
                            
                            for _ in range(sig["max"]):
                                extra = disk.read(chunk)
                                if not extra: break
                                if sig["end"] and sig["end"] in extra:
                                    end_idx = extra.find(sig["end"])
                                    raw += extra[:end_idx + len(sig["end"])]
                                    break
                                raw += extra
                            
                            if len(raw) < 500: continue 
                            if keyword_bytes and keyword_bytes not in raw: continue 
                            
                            h = hashlib.md5(raw[:4096]).hexdigest()
                            if h in self.seen_hashes: continue
                            
                            valid = True
                            dim = "-"
                            if sig["cat"] == "IMG":
                                try:
                                    img = Image.open(io.BytesIO(raw))
                                    img.load()
                                    w, h_px = img.size
                                    dim = f"{w}x{h_px}"
                                    if self.ignore_junk_var.get() and (w < 300 or h_px < 300): valid = False
                                except: valid = False
                            
                            if valid:
                                self.seen_hashes.add(h)
                                file_data = {"id": len(self.all_found_files), "data": raw, "type": fmt, "dim": dim, "size": len(raw)}
                                self.all_found_files.append(file_data)
                                
                                if time.time() - last_ui_update > 2.0:
                                    self.after(0, self.apply_sorting)
                                    last_ui_update = time.time()

                    offset += step
                    
                    if (abs(offset) // chunk) % 50 == 0:
                        prog_val = (total - offset) / total if is_reverse else offset / total
                        self.after(0, self.update_prog, prog_val, offset)

        except Exception as e:
            self.after(0, lambda: self.log(f"Erro: {e}"))
        
        self.is_scanning = False
        self.after(0, self.update_texts)
        self.after(0, lambda: self.scan_filter.configure(state="normal"))
        self.after(0, lambda: self.scan_order_combo.configure(state="normal"))
        self.after(0, self.apply_sorting)

    def update_prog(self, pct, offset):
        self.prog_bar.set(abs(pct))
        self.lbl_status.configure(text=f"{abs(offset)/(1024**3):.2f} GB")

    def apply_sorting(self, _=None):
        t = TRANSLATIONS[self.lang]
        mode = self.sort_combo.get()
        temp_list = self.all_found_files[:]
        
        is_type = mode in [t["sort_type"], TRANSLATIONS["en"]["sort_type"], TRANSLATIONS["pt"]["sort_type"]]
        is_size = mode in [t["sort_size"], TRANSLATIONS["en"]["sort_size"], TRANSLATIONS["pt"]["sort_size"]]

        if is_type: 
            temp_list.sort(key=lambda x: x["type"])
        elif is_size: 
            temp_list.sort(key=lambda x: x["size"], reverse=True)
        
        self.display_files = temp_list
        count = len(self.display_files)
        
        if count == 0:
            self.total_pages, self.current_page = 0, 0
        else:
            self.total_pages = math.ceil(count / max(1, self.items_per_page))
            if self.current_page >= self.total_pages: self.current_page = 0
            
        self.update_gallery_view()

    def update_gallery_view(self):
        for w in self.gallery_area.winfo_children(): w.destroy()
        self.page_images_cache = [] 
        
        if not self.display_files:
            self.lbl_page.configure(text="...")
            return
            
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = self.display_files[start:end]
        
        self.lbl_page.configure(text=f"Pág {self.current_page + 1}/{self.total_pages}")
        self.btn_prev.configure(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.current_page < self.total_pages - 1 else "disabled")
        
        area_width = self.gallery_area.winfo_width()
        if area_width < 100: area_width = 800
        max_cols = max(1, area_width // 145)
        for i in range(max_cols): self.gallery_area.columnconfigure(i, weight=1)
        
        row, col = 0, 0
        for item in page_items:
            thumb_obj = None
            if item["type"] in ["JPG", "PNG"]:
                try:
                    pil_img = Image.open(io.BytesIO(item["data"]))
                    pil_img.thumbnail((100, 100))
                    thumb_obj = ctk.CTkImage(pil_img, size=pil_img.size)
                except: pass
            
            if not thumb_obj:
                ph = Image.new('RGB', (100, 100), '#333')
                d = ImageDraw.Draw(ph)
                d.text((20, 40), item["type"], fill="white")
                thumb_obj = ctk.CTkImage(ph, size=(100, 100))
            
            self.page_images_cache.append(thumb_obj)
            
            text_lbl = f"{item['type']}\n{item['size']/1024:.0f} KB"
            btn = ctk.CTkButton(self.gallery_area, text=text_lbl, image=thumb_obj, compound="top",
                                width=120, height=120, fg_color="#2b2b2b", hover_color="#2ecc71",
                                command=lambda x=item: self.show_preview(x))
            btn.grid(row=row, column=col, padx=5, pady=5)
            
            col += 1
            if col >= max_cols: col = 0; row += 1

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_gallery_view()

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_gallery_view()

    def show_preview(self, item):
        self.selected_item = item
        self.current_preview_obj = None
        
        info = f"ID: {item['id']}\nType: {item['type']}\nDim: {item['dim']}\nSize: {item['size']/1024:.2f} KB"
        self.txt_content.delete("1.0", "end")
        
        if item["type"] == "JSON":
            try:
                txt = item["data"].decode('utf-8', errors='ignore')[:1000]
                self.txt_content.insert("1.0", txt)
            except: self.txt_content.insert("1.0", "Binário")
        else:
            self.txt_content.insert("1.0", info) 
            
        if item["type"] in ["JPG", "PNG"]:
            try:
                pil_img = Image.open(io.BytesIO(item["data"]))
                pil_img.thumbnail((280, 280))
                self.current_preview_obj = ctk.CTkImage(pil_img, size=pil_img.size)
                self.lbl_prev_img.configure(image=self.current_preview_obj, text="")
            except: self.lbl_prev_img.configure(image=None, text="Erro Imagem")
        else:
            self.lbl_prev_img.configure(image=None, text=f"Arquivo {item['type']}")
        self.btn_save.configure(state="normal")

    def save_current(self):
        if not hasattr(self, 'selected_item'): return
        item = self.selected_item
        ext = f".{item['type'].lower()}"
        path = filedialog.asksaveasfilename(defaultextension=ext, initialfile=f"AlabRecover_{item['id']}{ext}")
        if path:
            with open(path, "wb") as f: f.write(item["data"])

if __name__ == "__main__":
    if is_admin():
        app = AlabRecoveryTool()
        app.mainloop()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)