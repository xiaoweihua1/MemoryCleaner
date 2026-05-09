#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ctypes, psutil, time, os, threading
import tkinter as tk
from tkinter import ttk

kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

def get_foreground_pid():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value

def empty_working_set(pid):
    handle = kernel32.OpenProcess(0x1F0FFF, False, pid)
    if handle:
        psapi.EmptyWorkingSet(handle)
        kernel32.CloseHandle(handle)
        return True
    return False

def clean_memory(log_callback=None):
    fore_pid = get_foreground_pid()
    excluded = [0, 4, fore_pid]
    total_freed = 0
    count = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            pid = proc.info['pid']
            name = proc.info['name'].lower()
            if pid in excluded: continue
            if name in ('csrss.exe', 'wininit.exe', 'services.exe', 'lsass.exe', 'svchost.exe'):
                continue
            before = proc.memory_info().rss
            if empty_working_set(pid):
                after = proc.memory_info().rss
                freed = (before - after) / 1024 / 1024
                if freed > 1:
                    total_freed += freed
                    count += 1
                    if log_callback:
                        log_callback(f"  {name} 释放 {freed:.0f}MB")
        except: pass
    if log_callback:
        log_callback(f"共清理 {count} 个进程，释放 {total_freed:.0f}MB")

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("内存清理")
        self.root.geometry("460x440")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f0f0")
        
        self.timer_running = False
        self.interval = tk.IntVar(value=30)
        
        # 标题
        tk.Label(self.root, text="内存清理", font=("Microsoft YaHei", 16, "bold"),
                bg="#f0f0f0").pack(pady=(15,5))
        tk.Label(self.root, text="清理后台缓存，不影响正在运行的程序",
                font=("Microsoft YaHei", 9), fg="#666", bg="#f0f0f0").pack()
        
        # 一键清理
        tk.Button(self.root, text="一键清理", command=self.clean_now,
                 font=("Microsoft YaHei", 12), width=15, height=1,
                 relief="solid", bd=1, cursor="hand2").pack(pady=18)
        
        # 分隔线
        tk.Frame(self.root, height=1, bg="#ccc").pack(fill=tk.X, padx=40)
        
        # 定时设置
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(pady=15)
        tk.Label(frame, text="定时清理：每", font=("Microsoft YaHei", 9),
                bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Spinbox(frame, from_=1, to=120, textvariable=self.interval, width=4,
                  font=("Microsoft YaHei", 9), justify=tk.CENTER).pack(side=tk.LEFT, padx=4)
        tk.Label(frame, text="分钟自动清理一次", font=("Microsoft YaHei", 9),
                bg="#f0f0f0").pack(side=tk.LEFT)
        
        # 定时控制
        btn_frame = tk.Frame(self.root, bg="#f0f0f0")
        btn_frame.pack(pady=8)
        self.start_btn = tk.Button(btn_frame, text="启动定时", command=self.start_timer,
                                  font=("Microsoft YaHei", 9), width=10, relief="solid", bd=1)
        self.start_btn.pack(side=tk.LEFT, padx=4)
        self.stop_btn = tk.Button(btn_frame, text="停止定时", command=self.stop_timer,
                                 font=("Microsoft YaHei", 9), width=10, relief="solid", bd=1,
                                 state="disabled")
        self.stop_btn.pack(side=tk.LEFT, padx=4)
        
        # 状态
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(self.root, textvariable=self.status_var, font=("Microsoft YaHei", 9),
                fg="#333", bg="#f0f0f0").pack(pady=5)
        
        # 日志
        tk.Label(self.root, text="清理记录：", font=("Microsoft YaHei", 9),
                bg="#f0f0f0").pack(anchor=tk.W, padx=20)
        log_frame = tk.Frame(self.root, bg="#f0f0f0")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5,15))
        self.log_text = tk.Text(log_frame, height=9, font=("Consolas", 9),
                                bg="white", fg="#333", relief="solid", bd=1)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scroll.set)
        
        self.timer = None
        self.clean_count = 0

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def clean_now(self):
        now = time.strftime("%H:%M:%S")
        self.log(f"[{now}] 开始清理...")
        clean_memory(self.log)

    def timer_loop(self):
        if not self.timer_running: return
        self.clean_count += 1
        now = time.strftime("%H:%M:%S")
        self.log(f"[{now}] 第 {self.clean_count} 次定时清理...")
        clean_memory(self.log)
        self.timer = threading.Timer(self.interval.get() * 60, self.timer_loop)
        self.timer.daemon = True
        self.timer.start()

    def start_timer(self):
        self.timer_running = True
        self.clean_count = 0
        self.status_var.set(f"运行中 - 每 {self.interval.get()} 分钟自动清理")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.timer_loop()
        now = time.strftime("%H:%M:%S")
        self.log(f"[{now}] 定时清理已启动（间隔 {self.interval.get()} 分钟）")

    def stop_timer(self):
        self.timer_running = False
        if self.timer: self.timer.cancel()
        self.status_var.set("已停止")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        now = time.strftime("%H:%M:%S")
        self.log(f"[{now}] 定时清理已停止")

    def run(self): self.root.mainloop()

if __name__ == "__main__":
    App().run()
