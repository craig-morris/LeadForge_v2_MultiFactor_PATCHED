import os, threading, queue, time, webbrowser
import tkinter as tk
from tkinter import ttk, filedialog
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.csv_io import read_csv, write_csv, guess_columns
from core.constants import ENRICHMENT_COLUMNS
from core.cache import Cache
from core.checkpoint import Checkpoint
from core.rate_limiter import RateLimiter
from core.search_engine import SearchEngine
from core.website_scraper import WebsiteScraper
from core.social_finder import SocialFinder
from core.directory_checker import DirectoryChecker
from core.enricher import Enricher
from .styles import *
from .widgets import StatCard
from .dialogs import error, ask_resume, info

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("LeadForge — Local Business Enrichment"); self.geometry("1120x760"); self.configure(bg=CLOUD)
        self.events=queue.Queue(); self.stop_event=threading.Event(); self.pause_event=threading.Event(); self.pause_event.set(); self.rows=[]; self.fields=[]; self.output=""
        self.build(); self.after(100,self.drain)
    def build(self):
        head=tk.Frame(self,bg=NAVY,height=58); head.pack(fill="x"); tk.Label(head,text="LeadForge",fg="white",bg=NAVY,font=("Segoe UI",22,"bold")).pack(side="left",padx=20); tk.Label(head,text="Local Business Enrichment",fg="#dbe5f2",bg=NAVY,font=("Segoe UI",10)).pack(side="left")
        cfg=tk.LabelFrame(self,text="Configuration",bg=CLOUD,fg=CHARCOAL,padx=12,pady=8); cfg.pack(fill="x",padx=14,pady=12)
        self.csv=tk.StringVar(); self.outdir=tk.StringVar(value=os.getcwd()); self.namecol=tk.StringVar(); self.addrcol=tk.StringVar(); self.workers=tk.IntVar(value=10); self.delay=tk.DoubleVar(value=0.75)
        self._file_row(cfg,"Input CSV",self.csv,lambda:self.pick_csv()); self._file_row(cfg,"Output folder",self.outdir,lambda:self.pick_dir())
        row=ttk.Frame(cfg); row.pack(fill="x",pady=5); ttk.Label(row,text="Name column").pack(side="left"); self.namebox=ttk.Combobox(row,textvariable=self.namecol,state="readonly",width=28); self.namebox.pack(side="left",padx=6); ttk.Label(row,text="Address column").pack(side="left",padx=(20,0)); self.addrbox=ttk.Combobox(row,textvariable=self.addrcol,state="readonly",width=32); self.addrbox.pack(side="left",padx=6); ttk.Label(row,text="Workers").pack(side="left",padx=(20,0)); ttk.Spinbox(row,from_=1,to=20,textvariable=self.workers,width=5).pack(side="left"); ttk.Label(row,text="Delay/sec").pack(side="left",padx=(15,0)); ttk.Spinbox(row,from_=0.5,to=10,increment=.5,textvariable=self.delay,width=6).pack(side="left")
        self.website=tk.BooleanVar(value=True); self.email=tk.BooleanVar(value=True); self.phone=tk.BooleanVar(value=True); self.social=tk.BooleanVar(value=True); self.direct=tk.BooleanVar(value=True)
        row=ttk.Frame(cfg); row.pack(fill="x",pady=3)
        for txt,var in (("Website",self.website),("Email",self.email),("Phone",self.phone),("Socials",self.social),("Directories",self.direct)): ttk.Checkbutton(row,text=txt,variable=var).pack(side="left",padx=8)
        act=ttk.Frame(self); act.pack(fill="x",padx=14,pady=2); self.start=ttk.Button(act,text="▶ START",command=self.start_run); self.start.pack(side="left",padx=3); self.pause=ttk.Button(act,text="⏸ PAUSE",command=self.toggle_pause,state="disabled"); self.pause.pack(side="left",padx=3); self.stop=ttk.Button(act,text="⏹ STOP",command=self.stop_run,state="disabled"); self.stop.pack(side="left",padx=3); ttk.Button(act,text="🔄 RESUME",command=self.resume_run).pack(side="left",padx=3); ttk.Button(act,text="📂 OPEN OUTPUT",command=self.open_output).pack(side="right")
        self.progress=ttk.Progressbar(self,mode="determinate"); self.progress.pack(fill="x",padx=14,pady=10); self.proglabel=tk.StringVar(value="Ready"); ttk.Label(self,textvariable=self.proglabel).pack(anchor="w",padx=14)
        cards=ttk.Frame(self); cards.pack(fill="x",padx=14,pady=8); self.cards={k:StatCard(cards,k.upper()) for k in ("enriched","partial","failed","skipped")}; [v.pack(side="left",fill="x",expand=True,padx=4) for v in self.cards.values()]
        self.log=tk.Text(self,bg=CHARCOAL,fg="white",height=18,relief="flat"); self.log.pack(fill="both",expand=True,padx=14,pady=8); self.log.tag_config("success",foreground="#b7f7c5"); self.log.tag_config("warning",foreground="#ffd98a"); self.log.tag_config("error",foreground="#ffaaa7")
    def _file_row(self,p,label,var,cmd):
        r=ttk.Frame(p); r.pack(fill="x",pady=3); ttk.Label(r,text=label,width=16).pack(side="left"); ttk.Entry(r,textvariable=var).pack(side="left",fill="x",expand=True); ttk.Button(r,text="Browse…",command=cmd).pack(side="left",padx=5)
    def pick_csv(self):
        p=filedialog.askopenfilename(filetypes=[("CSV","*.csv"),("All","*.*")]);
        if not p:return
        self.csv.set(p)
        try:
            fields,_=read_csv(p); self.namebox["values"]=fields; self.addrbox["values"]=fields; n,a=guess_columns(fields); self.namecol.set(n); self.addrcol.set(a)
        except Exception as e:error("CSV error",str(e))
    def pick_dir(self):
        p=filedialog.askdirectory(); self.outdir.set(p) if p else None
    def emit(self,msg,level="info"): self.events.put(("log",msg,level))
    def start_run(self): self.run(False)
    def resume_run(self): self.run(True)
    def run(self,resume):
        if not self.csv.get(): return error("Input required","Choose a CSV first.")
        try:self.fields,self.rows=read_csv(self.csv.get())
        except Exception as e:return error("CSV error",str(e))
        if not self.namecol.get() or not self.addrcol.get(): return error("Mapping required","Choose name and address columns.")
        self.stop_event.clear(); self.pause_event.set(); self.start.config(state="disabled"); self.pause.config(state="normal"); self.stop.config(state="normal")
        threading.Thread(target=self.worker,args=(resume,),daemon=True).start()
    def toggle_pause(self):
        if self.pause_event.is_set(): self.pause_event.clear(); self.pause.config(text="▶ CONTINUE")
        else: self.pause_event.set(); self.pause.config(text="⏸ PAUSE")
    def stop_run(self): self.stop_event.set(); self.pause_event.set(); self.emit("Stop requested; current rows will finish cleanly.","warning")
    def worker(self,resume):
        cache = None
        try:
            os.makedirs(self.outdir.get(),exist_ok=True); self.output=os.path.join(self.outdir.get(),os.path.splitext(os.path.basename(self.csv.get()))[0]+"_enriched.csv")
            runtime_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime")
            os.makedirs(runtime_dir, exist_ok=True)
            cache = Cache(os.path.join(runtime_dir, "cache", "enrichment_cache.db"))
            cp = Checkpoint(os.path.join(runtime_dir, "checkpoint"))
            state=cp.load(self.csv.get()) if resume else None; start=(state or {}).get("next_index",0); self.emit(f"Starting {len(self.rows)} rows at index {start}.")
            limiter=RateLimiter(self.delay.get()); search=SearchEngine(limiter); scraper=WebsiteScraper(search,limiter); enr=Enricher(search,scraper,SocialFinder(search),DirectoryChecker(search),cache,checkpoint=cp,logger=self.emit)
            results=[None]*len(self.rows); counts={k:0 for k in self.cards}
            next_index=start
            scope={"website":self.website.get(),"socials":self.social.get(),"directories":self.direct.get()}
            with ThreadPoolExecutor(max_workers=max(1,int(self.workers.get()))) as pool:
                for batch_start in range(start,len(self.rows),max(1,int(self.workers.get())*2)):
                    if self.stop_event.is_set(): break
                    self.pause_event.wait()
                    batch_end=min(len(self.rows),batch_start+max(1,int(self.workers.get())*2))
                    futures={pool.submit(enr.enrich,self.rows[i],self.namecol.get(),self.addrcol.get(),scope):i for i in range(batch_start,batch_end)}
                    for fut in as_completed(futures):
                        i=futures[fut]
                        try: results[i]=fut.result()
                        except Exception as ex:
                            results[i]={**self.rows[i],"enrichment_status":"failed","enrichment_notes":f"{type(ex).__name__}: {ex}"}
                        st=results[i].get("enrichment_status","partial")
                        st="enriched" if st=="success" else st
                        counts[st]=counts.get(st,0)+1
                        next_index=max(next_index,i+1)
                        self.events.put(("stat",counts.copy())); self.events.put(("progress",next_index,len(self.rows)))
                    write_csv(self.output,self.fields,[r for r in results if r is not None]); cp.save(self.csv.get(),{"next_index":next_index})
            write_csv(self.output,self.fields,[r for r in results if r is not None]);
            if self.stop_event.is_set():
                counts["skipped"] += max(0, len(self.rows) - next_index)
                self.emit("Stopped safely. Use Resume to continue.","warning")
            else:
                cp.clear(self.csv.get())
                counts["skipped"] = max(0, len(self.rows) - sum(counts.get(k,0) for k in ("enriched","partial","failed")))
                self.emit(
                    f"Completed. Enriched: {counts.get('enriched',0)} | "
                    f"Partial: {counts.get('partial',0)} | "
                    f"Skipped: {counts.get('skipped',0)} | "
                    f"Failed: {counts.get('failed',0)} | Output: {self.output}",
                    "success",
                )
                self.events.put(("stat",counts.copy()))
        except Exception as e:self.emit(f"Fatal error: {type(e).__name__}: {e}","error")
        finally:
            if cache is not None:
                cache.close()
            self.events.put(("done",))
    def drain(self):
        try:
            while True:
                e=self.events.get_nowait(); typ=e[0]
                if typ=="log": self.log.insert("end",e[1]+"\n",e[2]); self.log.see("end")
                elif typ=="stat":
                    for k,v in e[1].items(): self.cards.get(k,StatCard).set(v) if k in self.cards else None
                elif typ=="progress": self.progress["maximum"]=e[2]; self.progress["value"]=e[1]; self.proglabel.set(f"Enriching {e[1]}/{e[2]} — {int(e[1]/e[2]*100)}%")
                elif typ=="done": self.start.config(state="normal"); self.pause.config(state="disabled",text="⏸ PAUSE"); self.stop.config(state="disabled")
        except queue.Empty: pass
        self.after(100,self.drain)
    def open_output(self):
        if self.output and os.path.exists(self.output): webbrowser.open("file://"+os.path.abspath(self.output))
        else: info("Output","No output file has been created yet.")
