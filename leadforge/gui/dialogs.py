from tkinter import messagebox

def error(title,msg): messagebox.showerror(title,msg)
def info(title,msg): messagebox.showinfo(title,msg)
def ask_resume(): return messagebox.askyesno("Resume", "A checkpoint exists for this input. Resume it?")
