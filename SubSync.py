import os
import sys
import shutil
import subprocess
import threading
import re
import glob
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox

# ==========================================
#  STARTUP: HANDLE BUNDLED FFMPEG
# ==========================================
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ffmpeg_dir = resource_path("")
os.environ["PATH"] += os.pathsep + ffmpeg_dir

# ==========================================
#  BACKEND LOGIC
# ==========================================

def extract_season_episode(filename):
    name = filename.lower()
    match = re.search(r's(\d+)[._-]*e(\d+)', name)
    if match: return (int(match.group(1)), int(match.group(2)))
    match = re.search(r'(\d+)x(\d+)', name)
    if match: return (int(match.group(1)), int(match.group(2)))
    return None

def find_best_subtitle(video_path, subtitle_files):
    video_filename = os.path.basename(video_path)
    video_se = extract_season_episode(video_filename)
    
    # 1. Smart Match
    if video_se:
        vid_season, vid_episode = video_se
        for sub_path in subtitle_files:
            sub_filename = os.path.basename(sub_path)
            sub_se = extract_season_episode(sub_filename)
            if sub_se:
                sub_season, sub_episode = sub_se
                if vid_season == sub_season and vid_episode == sub_episode:
                    return sub_path, f"S{vid_season:02d}E{vid_episode:02d}"

    # 2. Exact Name Match
    video_base = os.path.splitext(video_filename)[0]
    for sub_path in subtitle_files:
        sub_base = os.path.splitext(os.path.basename(sub_path))[0]
        if video_base.lower() == sub_base.lower():
             return sub_path, "Exact Match"
    return None, None

def run_ffsubsync(video_path, sub_path, output_path):
    cmd = ["ffsubsync", video_path, "-i", sub_path, "-o", output_path]
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.run(cmd, check=True, startupinfo=startupinfo)

# ==========================================
#  GUI CLASS
# ==========================================

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SubSyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SubSync")
        self.geometry("800x800")
        self.resizable(True, True)

        # Container for checkboxes
        self.checkboxes = []
        self.video_map = {} # Maps checkbox text to full path
        self.current_folder = ""

        # --- HEADER ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(pady=10)
        ctk.CTkLabel(self.header_frame, text="SubSync", font=("Roboto Medium", 24)).pack()
        
        # --- TAB VIEW ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(pady=10, padx=20, fill="both", expand=True)
        
        self.tab_dir = self.tabview.add("Directory Mode")
        self.tab_single = self.tabview.add("Manual Single File")

        # ==========================
        # TAB 1: DIRECTORY MODE
        # ==========================
        
        # 1. Selection Row
        self.dir_frame = ctk.CTkFrame(self.tab_dir, fg_color="transparent")
        self.dir_frame.pack(fill="x", padx=10, pady=10)

        self.entry_folder = ctk.CTkEntry(self.dir_frame, placeholder_text="Select folder to see videos...", width=400)
        self.entry_folder.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_browse = ctk.CTkButton(self.dir_frame, text="Browse Folder", width=100, command=self.browse_folder)
        self.btn_browse.pack(side="right")

        # 2. Control Row (Select All / Sync)
        self.ctrl_frame = ctk.CTkFrame(self.tab_dir, fg_color="transparent")
        self.ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_select_all = ctk.CTkButton(self.ctrl_frame, text="Select All", width=80, fg_color="gray", command=self.select_all)
        self.btn_select_all.pack(side="left", padx=(0, 10))
        
        self.btn_deselect_all = ctk.CTkButton(self.ctrl_frame, text="Deselect All", width=80, fg_color="gray", command=self.deselect_all)
        self.btn_deselect_all.pack(side="left")

        self.lbl_count = ctk.CTkLabel(self.ctrl_frame, text="0 videos found", text_color="gray")
        self.lbl_count.pack(side="right")

        # 3. Scrollable Video List
        self.scroll_frame = ctk.CTkScrollableFrame(self.tab_dir, label_text="Videos Found (Check to Sync)")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 4. Action Button
        self.btn_sync_selected = ctk.CTkButton(self.tab_dir, text="SYNC SELECTED VIDEOS", font=("Roboto Medium", 15), 
                                               height=45, fg_color="#1F6AA5", command=self.start_list_thread)
        self.btn_sync_selected.pack(pady=10, padx=10, fill="x")


        # ==========================
        # TAB 2: MANUAL SINGLE
        # ==========================
        ctk.CTkLabel(self.tab_single, text="Video File:", font=("Roboto", 13)).pack(anchor="w", padx=20, pady=(20, 5))
        self.frame_vid = ctk.CTkFrame(self.tab_single, fg_color="transparent")
        self.frame_vid.pack(fill="x", padx=20)
        self.entry_vid = ctk.CTkEntry(self.frame_vid, placeholder_text="Path to .mp4...")
        self.entry_vid.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(self.frame_vid, text="Select", width=60, command=lambda: self.browse_file(self.entry_vid, "vid")).pack(side="right")

        ctk.CTkLabel(self.tab_single, text="Subtitle File:", font=("Roboto", 13)).pack(anchor="w", padx=20, pady=(20, 5))
        self.frame_sub = ctk.CTkFrame(self.tab_single, fg_color="transparent")
        self.frame_sub.pack(fill="x", padx=20)
        self.entry_sub = ctk.CTkEntry(self.frame_sub, placeholder_text="Path to .srt...")
        self.entry_sub.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(self.frame_sub, text="Select", width=60, command=lambda: self.browse_file(self.entry_sub, "sub")).pack(side="right")

        self.btn_run_single = ctk.CTkButton(self.tab_single, text="SYNC THIS FILE", font=("Roboto Medium", 15), 
                                            height=45, fg_color="#E07A5F", command=self.start_single_thread)
        self.btn_run_single.pack(pady=40)


        # ==========================
        # SHARED LOGS
        # ==========================
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=(10, 5))
        
        self.lbl_status = ctk.CTkLabel(self, text="Ready", font=("Roboto", 12), text_color="gray")
        self.lbl_status.pack(pady=(0, 5))

        self.console_box = ctk.CTkTextbox(self, height=120, corner_radius=10)
        self.console_box.pack(fill="x", padx=20, pady=(0, 20))
        self.console_box.configure(state="disabled")

    # --- LIST LOGIC ---

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, folder)
            self.current_folder = folder
            self.refresh_video_list(folder)

    def refresh_video_list(self, folder):
        # Clear old checkboxes
        for cb in self.checkboxes:
            cb.destroy()
        self.checkboxes.clear()
        self.video_map.clear()

        # Find videos (NON-RECURSIVE, immediate folder only)
        video_exts = ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.flv', '*.wmv']
        found_videos = []
        for ext in video_exts:
            found_videos.extend(glob.glob(os.path.join(folder, ext)))

        self.lbl_count.configure(text=f"{len(found_videos)} videos found")

        # Create Checkboxes
        if not found_videos:
            lbl = ctk.CTkLabel(self.scroll_frame, text="No videos found in this folder.")
            lbl.pack(pady=10)
            self.checkboxes.append(lbl) # track to destroy later
            return

        for vid_path in found_videos:
            name = os.path.basename(vid_path)
            cb = ctk.CTkCheckBox(self.scroll_frame, text=name, hover_color="#1F6AA5")
            cb.pack(anchor="w", padx=10, pady=5)
            self.checkboxes.append(cb)
            self.video_map[name] = vid_path # Map name to full path

    def select_all(self):
        for cb in self.checkboxes:
            if isinstance(cb, ctk.CTkCheckBox):
                cb.select()

    def deselect_all(self):
        for cb in self.checkboxes:
            if isinstance(cb, ctk.CTkCheckBox):
                cb.deselect()

    def browse_file(self, entry, type_):
        filetypes = [("Video", "*.mp4 *.mkv")] if type_ == "vid" else [("Sub", "*.srt")]
        f = filedialog.askopenfilename(filetypes=filetypes)
        if f:
            entry.delete(0, "end")
            entry.insert(0, f)

    # --- LOGGING ---
    def log(self, message, error=False):
        self.console_box.configure(state="normal")
        tag = "ERR" if error else "INFO"
        self.console_box.insert("end", f"[{tag}] {message}\n")
        self.console_box.see("end")
        self.console_box.configure(state="disabled")

    def toggle_ui(self, state):
        self.btn_sync_selected.configure(state=state)
        if state == "disabled":
            self.console_box.configure(state="normal")
            self.console_box.delete("1.0", "end")
            self.console_box.configure(state="disabled")

    # --- THREADS ---

    def start_list_thread(self):
        # 1. Gather Selected Files
        selected_paths = []
        for cb in self.checkboxes:
            if isinstance(cb, ctk.CTkCheckBox) and cb.get() == 1:
                name = cb.cget("text")
                selected_paths.append(self.video_map[name])
        
        if not selected_paths:
            messagebox.showwarning("Warning", "No videos selected!")
            return
            
        self.toggle_ui("disabled")
        threading.Thread(target=self.run_list_logic, args=(self.current_folder, selected_paths), daemon=True).start()

    def start_single_thread(self):
        vid = self.entry_vid.get()
        sub = self.entry_sub.get()
        if not os.path.exists(vid) or not os.path.exists(sub):
            messagebox.showerror("Error", "Check files")
            return
        self.toggle_ui("disabled")
        threading.Thread(target=self.run_manual_logic, args=(vid, sub), daemon=True).start()

    # --- CORE PROCESSING ---

    def run_list_logic(self, folder, video_paths):
        self.log(f"Processing {len(video_paths)} selected videos...")
        
        # Gather all subtitles in the folder once
        sub_exts = ['*.srt', '*.vtt']
        subtitle_files = []
        for ext in sub_exts:
            subtitle_files.extend(glob.glob(os.path.join(folder, ext)))

        success = 0
        total = len(video_paths)

        for i, vid_path in enumerate(video_paths):
            vid_name = os.path.basename(vid_path)
            self.progress_bar.set((i)/total)
            self.lbl_status.configure(text=f"Syncing: {vid_name}")
            
            # Find match
            matched_sub, _ = find_best_subtitle(vid_path, subtitle_files)
            
            if matched_sub:
                sub_name = os.path.basename(matched_sub)
                self.log(f"Matched {vid_name} -> {sub_name}")
                
                # Backup logic
                backup_dir = os.path.join(folder, "old_subtitles")
                if not os.path.exists(backup_dir): os.makedirs(backup_dir)
                
                # Copy original sub to backup if not there
                dest_backup = os.path.join(backup_dir, sub_name)
                source_for_sync = matched_sub
                
                try:
                    if os.path.exists(matched_sub) and matched_sub != dest_backup:
                        shutil.copy2(matched_sub, dest_backup)
                        source_for_sync = dest_backup # use the backup as reference
                    
                    # Output (overwrite the subtitle file next to the video)
                    # Often the matched sub is named differently, we usually want output named like video
                    out_name = os.path.splitext(vid_name)[0] + os.path.splitext(sub_name)[1]
                    out_path = os.path.join(folder, out_name)
                    
                    run_ffsubsync(vid_path, source_for_sync, out_path)
                    self.log("  -> Success")
                    success += 1
                except Exception as e:
                    self.log(f"  -> Error: {e}", error=True)
            else:
                self.log(f"Skipping {vid_name}: No matching subtitle found in folder.", error=True)

        self.progress_bar.set(1.0)
        self.lbl_status.configure(text="Complete")
        self.toggle_ui("normal")
        messagebox.showinfo("Done", f"Batch Complete.\nSynced: {success}/{total}")

    def run_manual_logic(self, vid_path, sub_path):
        self.log("Manual Sync Started...")
        self.progress_bar.set(0.2)
        try:
            # Backup
            bk_dir = os.path.join(os.path.dirname(sub_path), "original_subs")
            if not os.path.exists(bk_dir): os.makedirs(bk_dir)
            bk_path = os.path.join(bk_dir, os.path.basename(sub_path))
            shutil.copy2(sub_path, bk_path)
            
            run_ffsubsync(vid_path, bk_path, sub_path)
            self.log("Success!")
            messagebox.showinfo("Success", "File Synced")
        except Exception as e:
            self.log(f"Error: {e}", error=True)
        
        self.progress_bar.set(1.0)
        self.toggle_ui("normal")

if __name__ == "__main__":
    app = SubSyncApp()
    app.mainloop()