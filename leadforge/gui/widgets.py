import tkinter as tk
from tkinter import ttk
from .styles import *

class StatCard(ttk.Frame):
    def __init__(self,parent,label):
        super().__init__(parent); self.value=tk.StringVar(value="0")
        ttk.Label(self,textvariable=self.value,font=("Segoe UI",18,"bold")).pack(pady=(8,0)); ttk.Label(self,text=label).pack(pady=(0,8))
    def set(self,n): self.value.set(str(n))
