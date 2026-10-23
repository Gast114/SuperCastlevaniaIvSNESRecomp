"""Separate desktop enemy workshop using the original engine, not GIF playback."""
import argparse
import json
import os
from pathlib import Path
import queue
import threading
import time
import zipfile
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from PIL import Image,ImageDraw,ImageOps,ImageTk
from enemy_workshop_native import NativeSession,ROOT
from enemy_workshop_assets import Workspace

DEFAULT_WORKSPACE=ROOT.parent/'Assets (ausgeschnitten)'/'Gegner'/'Werkstatt'


def preview(snapshot,workspace,custom,size,follow=True,background='#19212c'):
    """Render two views of the same native field; custom PNGs keep their canvas."""
    width,height=size
    image=Image.new('RGBA',size,background)
    draw=ImageDraw.Draw(image)
    zoom=min(width/256,height/224)
    actors=snapshot.get('actors',[])
    main=next((a for a in actors if a['slot']==snapshot.get('target',0x580)),None)
    origin=(128-main['x'],128-main['y']) if follow and main else (0,0)
    def paste(identifier,actor,edited=False):
        source=workspace.image(identifier,edited)
        if source is None:return
        frame=workspace.frames[identifier];dw,dh=frame['display_size'];ax,ay=frame['anchor']
        flip=actor['flip']
        if flip&1:source=ImageOps.mirror(source)
        if flip&2:source=ImageOps.flip(source)
        source=source.resize((max(1,round(dw*zoom)),max(1,round(dh*zoom))),
                             Image.Resampling.LANCZOS if edited and workspace.edited(identifier) else Image.Resampling.NEAREST)
        x=actor['x']+origin[0]-(dw-ax if flip&1 else ax)
        y=actor['y']+origin[1]-(dh-ay if flip&2 else ay)
        image.alpha_composite(source,(round(x*zoom),round(y*zoom)))
    # Only the spawned group and its native children are shown. Room props
    # collected during scene setup are kept out of the neutral preview.
    jobs=[]
    for actor in actors:
        if actor['id'] not in workspace.frames:continue
        parts=sorted(actor['parts'],key=lambda p:p['oam'],reverse=True)
        uniform=len({(p['priority'],p.get('math',0)) for p in parts})<=1
        if custom and workspace.edited(actor['id']) and uniform:
            jobs.append((min(p['oam'] for p in parts),actor['id'],actor,True))
        elif parts and all(p['id'] in workspace.frames for p in parts):
            for part in parts:jobs.append((part['oam'],part['id'],actor,custom))
        else:
            jobs.append((min((p['oam'] for p in parts),default=127),actor['id'],actor,False))
    # OBJ overlap is decided by global OAM order, including projectiles from
    # other actors. OBJ priority only places the winner relative to backgrounds.
    for _,identifier,actor,edited in sorted(jobs,key=lambda item:item[0],reverse=True):
        paste(identifier,actor,edited)
    return image.convert('RGB')


class Worker(threading.Thread):
    def __init__(self,commands,events,rom,build):
        super().__init__(daemon=True);self.commands=commands;self.events=events
        self.rom=rom;self.build=build;self.stopping=False

    def publish(self,value):
        try:self.events.put_nowait(value)
        except queue.Full:
            try:self.events.get_nowait()
            except queue.Empty:pass
            self.events.put_nowait(value)

    def run(self):
        session=None
        allowed_ids=set()
        def allow(snapshot):
            for actor in snapshot.get('actors',[]):
                allowed_ids.add(actor['id'])
                allowed_ids.update(p['id'] for p in actor['parts'])
        try:
            session=NativeSession(self.rom,self.build);session.start()
            entry=next(e for e in session.catalog if e['type']==18 and e['variant']==0)
            snapshot=session.spawn(entry);paused=False;speed=1.;action='Natürlich';action_age=0;missing_age=0;collect=[]
            allow(snapshot)
            self.publish({'catalog':session.catalog,'references':str(session.references),'snapshot':snapshot,'status':'Native Laufzeit bereit'})
            deadline=time.monotonic()
            while not self.stopping:
                step=False;changed=False
                while True:
                    try:command=self.commands.get_nowait()
                    except queue.Empty:break
                    kind=command['kind']
                    if kind=='stop':self.stopping=True;break
                    try:
                        if kind=='spawn':
                            entry=command['entry'];snapshot=session.spawn(entry,command.get('count',1));action='Natürlich';action_age=0;changed=True;collect=[]
                        elif kind=='collect':
                            entry=command['entry'];snapshot=session.spawn(entry);action='Gehen';session.action(action)
                            action_age=0;collect=['Werfen','Zerfallen'];paused=False;changed=True
                        elif kind=='pause':paused=command['value']
                        elif kind=='step':step=True
                        elif kind=='speed':speed=command['value']
                        elif kind=='action':session.action(command['value']);action=command['value'];action_age=0;collect=[]
                        elif kind=='direction':
                            session.direction=1 if command['value']=='Rechts' else -1
                            x=session.read(session.target+0xa)
                            session.write({0x54a:x+(64 if command['value']=='Rechts' else -64)})
                    except Exception as error:self.publish({'error':str(error)})
                if self.stopping:break
                if changed:
                    allow(snapshot)
                    self.publish({'catalog':session.catalog,'references':str(session.references),'snapshot':snapshot,'allowed_ids':sorted(allowed_ids)})
                if not paused or step:
                    fields=1 if step else 2
                    snapshot=session.step(fields);action_age+=fields
                    missing_age=0 if any(a['type']==entry.get('main_type',entry['type']) for a in snapshot['actors']) else missing_age+fields
                    allow(snapshot)
                    # Re-run the real action routine; the animation itself is
                    # never approximated or driven by a hand-written pose list.
                    if collect and action_age>=80:
                        snapshot=session.spawn(entry);action=collect.pop(0);session.action(action);action_age=0
                    elif action in ('Werfen','Zerfallen') and action_age>=110:
                        snapshot=session.spawn(entry);session.action(action);action_age=0
                    elif action in ('Natürlich','Gehen') and missing_age>=(240 if entry.get('boss') else 120):
                        snapshot=session.spawn(entry);action_age=0;missing_age=0
                    self.publish({'catalog':session.catalog,'references':str(session.references),'snapshot':snapshot,'allowed_ids':sorted(allowed_ids),
                                  'status':f'Originalmotor · {session.elapsed} Felder · {action}'})
                deadline+=1/(30*speed)
                time.sleep(max(.001,min(.1,deadline-time.monotonic())))
                if deadline<time.monotonic()-.25:deadline=time.monotonic()
        except BaseException as error:self.publish({'fatal':str(error)})
        finally:
            if session:session.close()


class Workshop:
    def __init__(self,root,rom=None,build=None,workspace=DEFAULT_WORKSPACE):
        self.root=root;self.workspace=Workspace(workspace)
        root.title('Gegner-Werkstatt · Super Castlevania IV')
        scale=max(1.,float(root.tk.call('tk','scaling'))/(96/72),
                  min(root.winfo_screenwidth()/1920,root.winfo_screenheight()/1080))
        root.tk.call('tk','scaling',96/72*scale)
        root.geometry(f'{min(round(1500*scale),root.winfo_screenwidth()-60)}x{min(round(960*scale),root.winfo_screenheight()-80)}')
        root.minsize(round(900*scale),round(640*scale))
        style=ttk.Style();style.configure('.',font=('Segoe UI',11));style.configure('Treeview',rowheight=round(30*scale))
        self.commands=queue.Queue();self.events=queue.Queue(maxsize=8)
        self.snapshot={'actors':[]};self.catalog=[];self.references=None;self.photos=[];self.current_ids=[];self.allowed_ids=set()
        self.status=tk.StringVar(value='Werkstatt startet die eigene native Laufzeit …')
        self.pause=tk.BooleanVar(value=False);self.count=tk.IntVar(value=1);self.parts=tk.BooleanVar(value=False)
        self.enemy=tk.StringVar();self.action=tk.StringVar(value='Natürlich');self.speed=tk.StringVar(value='100%')
        self.follow=tk.BooleanVar(value=True);self.selected_id=None;self.list_signature=None
        self.only_current=tk.BooleanVar(value=True);self.active_entry={'type':18}
        self.collect_on_ready=not bool(self.workspace.frames);self.closing=False
        outer=ttk.Frame(root,padding=18);outer.pack(fill='both',expand=True)
        ttk.Label(outer,text='Gegner-Werkstatt',font=('Segoe UI',23,'bold')).pack(anchor='w')
        ttk.Label(outer,text='Original und dein Redesign · gleicher nativer Bewegungsablauf · PNGs werden live neu geladen').pack(anchor='w',pady=(0,14))
        controls=ttk.Frame(outer);controls.pack(fill='x')
        self.enemy_box=ttk.Combobox(controls,textvariable=self.enemy,state='readonly',width=42)
        self.enemy_box.pack(side='left',padx=(0,8))
        self.count_box=ttk.Spinbox(controls,from_=1,to=8,textvariable=self.count,width=3)
        self.count_box.pack(side='left',padx=5)
        ttk.Button(controls,text='Spawnen / neu starten',command=self.spawn).pack(side='left',padx=5)
        self.action_box=ttk.Combobox(controls,textvariable=self.action,values=['Natürlich','Gehen','Werfen','Zerfallen'],state='readonly',width=13)
        self.action_box.pack(side='left',padx=5);self.action_box.bind('<<ComboboxSelected>>',lambda _:self.send('action',value=self.action.get()))
        ttk.Button(controls,text='Links',command=lambda:self.send('direction',value='Links')).pack(side='left',padx=3)
        ttk.Button(controls,text='Rechts',command=lambda:self.send('direction',value='Rechts')).pack(side='left',padx=3)
        playback=ttk.Frame(outer);playback.pack(fill='x',pady=10)
        ttk.Checkbutton(playback,text='Pause',variable=self.pause,command=lambda:self.send('pause',value=self.pause.get())).pack(side='left')
        ttk.Button(playback,text='Ein Feld weiter',command=self.single_step).pack(side='left',padx=8)
        speed_box=ttk.Combobox(playback,textvariable=self.speed,values=['25%','50%','100%'],state='readonly',width=6)
        speed_box.pack(side='left');speed_box.bind('<<ComboboxSelected>>',lambda _:self.send('speed',value=int(self.speed.get()[:-1])/100))
        ttk.Checkbutton(playback,text='Figur zentrieren',variable=self.follow).pack(side='left',padx=18)
        ttk.Button(playback,text='Vollständige Skelett-Aktionen sammeln',command=self.collect).pack(side='left',padx=8)
        panes=ttk.Panedwindow(outer,orient='horizontal');panes.pack(fill='both',expand=True)
        pictures=ttk.Frame(panes);editor=ttk.Frame(panes,padding=(12,0,0,0));panes.add(pictures,weight=4);panes.add(editor,weight=2)
        compare=ttk.Frame(pictures);compare.pack(fill='both',expand=True)
        self.canvases=[]
        for title in ('Original','Dein Redesign – live'):
            frame=ttk.LabelFrame(compare,text=title,padding=3);frame.pack(side='left',fill='both',expand=True,padx=3)
            canvas=tk.Canvas(frame,bg='#19212c',highlightthickness=0);canvas.pack(fill='both',expand=True);self.canvases.append(canvas)
        ttk.Label(editor,text='Aufgenommene Posen und Geschosse',font=('Segoe UI',12,'bold')).pack(anchor='w')
        ttk.Checkbutton(editor,text='Einzelteile anzeigen / austauschen',variable=self.parts,command=self.refresh_list).pack(anchor='w',pady=8)
        ttk.Checkbutton(editor,text='Nur aktuelle Figur und zugeordnete Geschosse',variable=self.only_current,command=self.refresh_list).pack(anchor='w')
        list_frame=ttk.Frame(editor);list_frame.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(list_frame,show='tree',selectmode='browse',height=12)
        scrollbar=ttk.Scrollbar(list_frame,orient='vertical',command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set);self.tree.pack(side='left',fill='both',expand=True);scrollbar.pack(side='right',fill='y')
        self.tree.bind('<<TreeviewSelect>>',self.select)
        self.asset_preview=ttk.Label(editor);self.asset_preview.pack(anchor='center',pady=6)
        self.asset_photo=None
        self.file_label=tk.StringVar(value='PNG auswählen oder direkt in Photoshop bearbeiten.')
        ttk.Label(editor,textvariable=self.file_label,wraplength=370).pack(fill='x',pady=10)
        for text,command in [('PNG in Photoshop / Standardprogramm öffnen',self.open_png),('PNG ersetzen …',self.replace),
                             ('Arbeitsordner öffnen',lambda:os.startfile(self.workspace.folder)),('PNG-Sammlung als ZIP exportieren',self.export_collection),('Paket zum Einbauen erstellen',self.build_pack)]:
            ttk.Button(editor,text=text,command=command).pack(fill='x',pady=4)
        ttk.Label(outer,text='Ganze transparente Bildfläche behalten. Ganze Pose ersetzt ihre Einzelteile; ohne neue ganze Pose bleiben Teile einzeln austauschbar.',wraplength=1300).pack(anchor='w',pady=(10,4))
        ttk.Label(outer,textvariable=self.status,foreground='#35647d',wraplength=1400).pack(anchor='w')
        self.context=tk.StringVar(value='Skelett: 5 Körperposen, 3 Knochenbilder und Zerfall sind belegt. Weitere Figuren: bisher aufgenommener Umfang.')
        ttk.Label(outer,textvariable=self.context,wraplength=1400).pack(anchor='w')
        self.worker=Worker(self.commands,self.events,rom,build);self.worker.start()
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(50,self.tick)

    def send(self,kind,**values):self.commands.put(dict(kind=kind,**values))
    def single_step(self):
        self.pause.set(True);self.send('pause',value=True);self.send('step')
    def spawn(self):
        i=self.enemy_box.current()
        if i>=0:
            self.active_entry=self.catalog[i]
            self.action.set('Natürlich');self.send('spawn',entry=self.catalog[i],count=self.count.get())
            self.action_box.configure(values=['Natürlich','Gehen','Werfen','Zerfallen'] if self.catalog[i]['type'] in (17,18) else ['Natürlich'])
            entry=self.catalog[i]
            self.count_box.configure(state='disabled' if entry.get('boss') else 'normal')
            if entry.get('boss'):
                self.context.set(entry.get('coverage_note','Experimenteller Bosskontext: '+('native Darstellung geprüft; weitere Abläufe noch unvollständig.' if entry.get('preview_verified') else 'Initialisierung / Sichtbarkeit noch unvollständig.')))
            else:self.context.set(entry.get('verification','')+' · '+entry.get('action_coverage','Neue tatsächlich sichtbare Posen werden gesammelt.'))
    def collect(self):
        index=next((i for i,e in enumerate(self.catalog) if e['type']==18 and e['variant']==0),None)
        if index is None:return
        self.enemy_box.current(index);self.pause.set(False)
        self.active_entry=self.catalog[index]
        self.count_box.configure(state='normal')
        self.action_box.configure(values=['Natürlich','Gehen','Werfen','Zerfallen'])
        self.action.set('Gehen')
        self.context.set('Skelett: Gehen, Werfen mit Knochen und Zerfallen werden mit dem Originalmotor gesammelt.')
        self.send('collect',entry=self.catalog[index])
    def select(self,*_):
        selected=self.tree.selection();self.selected_id=selected[0] if selected else None
        if self.selected_id:
            frame=self.workspace.frames[self.selected_id]
            self.file_label.set(frame['image']+'\n'+str(self.workspace.folder/'artwork'))
    def refresh_list(self):self.list_signature=None
    def open_png(self):
        if self.selected_id:os.startfile(self.workspace.folder/'artwork'/self.workspace.frames[self.selected_id]['image'])
    def replace(self):
        if not self.selected_id:return
        path=filedialog.askopenfilename(parent=self.root,title='Fertiges PNG übernehmen',filetypes=[('PNG','*.png')])
        if path:
            try:self.workspace.replace(self.selected_id,path);self.status.set('PNG übernommen. Vorschau wird live aktualisiert.')
            except (ValueError,OSError) as error:messagebox.showerror('PNG nicht übernommen',str(error),parent=self.root)
    def build_pack(self):
        output=ROOT/'artwork-local/enemies'/('werkstatt-'+time.strftime('%Y%m%d-%H%M%S'))
        try:
            count=self.workspace.build_pack(output)
            self.status.set(f'{count} native Zuordnungen gepackt: {output}')
            os.startfile(output)
        except (ValueError,OSError) as error:messagebox.showinfo('Paket erstellen',str(error),parent=self.root)
    def export_collection(self):
        output=filedialog.asksaveasfilename(parent=self.root,title='PNG-Sammlung exportieren',defaultextension='.zip',filetypes=[('ZIP','*.zip')])
        if not output:return
        try:
            self.workspace.gallery()
            with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
                for name in ('project.json','VORLAGEN.html','HIER_STARTEN.txt'):
                    path=self.workspace.folder/name
                    if path.is_file():archive.write(path,path.name)
                for name in ('references','artwork'):
                    for path in (self.workspace.folder/name).glob('*.png'):
                        archive.write(path,path.relative_to(self.workspace.folder))
            self.status.set('PNG-Sammlung exportiert: '+output)
        except OSError as error:messagebox.showerror('Export angehalten',str(error),parent=self.root)
    def tick(self):
        if self.closing:return
        try:
            while True:
                event=self.events.get_nowait()
                if 'catalog' in event and not self.catalog:
                    groups={'enemy':'Gegner','object':'Objekt','hazard':'Gefahr','effect':'Effekt','unclassified':'Unbestimmt'}
                    order={'enemy':0,'object':2,'hazard':3,'effect':4,'unclassified':5}
                    self.catalog=sorted(event['catalog'],key=lambda e:(1 if e.get('boss') else order.get(e.get('category'),5),e['type'],e['variant']))
                    self.enemy_box.configure(values=[e['name'] if e.get('boss') else
                        f'{groups.get(e.get("category"),"Unbestimmt")} {e["type"]:02X} · {e["name"]}'+
                        (' · Kontext offen' if not e.get('native_verified') else '') for e in self.catalog])
                    self.enemy_box.current(next(i for i,e in enumerate(self.catalog) if e['type']==18 and not e['variant']))
                    if self.collect_on_ready:self.collect();self.collect_on_ready=False
                if 'references' in event:self.references=Path(event['references'])
                if 'snapshot' in event:self.snapshot=event['snapshot']
                if 'allowed_ids' in event:self.allowed_ids.update(event['allowed_ids'])
                self.status.set(event.get('fatal',event.get('error',event.get('status',self.status.get()))))
        except queue.Empty:pass
        if self.references:self.workspace.ingest(self.references,self.allowed_ids)
        family={self.active_entry['type'],*self.active_entry.get('child_types',[])}
        if self.active_entry['type'] in (17,18):family.update((17,18,2,45))
        frames=list({f['image']:f for f in self.workspace.frames.values()
                     if f.get('component',False)==self.parts.get() and
                     (not self.only_current.get() or f['actor_type'] in family)}.values())
        signature=tuple(f['id'] for f in frames)
        if signature!=self.list_signature:
            self.tree.delete(*self.tree.get_children())
            for f in frames:self.tree.insert('', 'end',iid=f['id'],text=f['label'])
            if frames:self.tree.selection_set(self.selected_id if self.selected_id in signature else frames[0]['id'])
            else:
                self.selected_id=None;self.asset_preview.configure(image='')
                self.file_label.set('Hier erscheinen die tatsächlich aufgenommenen PNGs dieser Figur.')
            self.list_signature=signature
        self.photos=[]
        if self.selected_id:
            asset=self.workspace.image(self.selected_id,True)
            if asset is not None:
                panel=Image.new('RGBA',(144,144),'#394550')
                panel.alpha_composite(asset.resize((144,144),Image.Resampling.NEAREST))
                self.asset_photo=ImageTk.PhotoImage(panel)
                self.asset_preview.configure(image=self.asset_photo)
        for i,canvas in enumerate(self.canvases):
            size=(max(2,canvas.winfo_width()),max(2,canvas.winfo_height()))
            picture=preview(self.snapshot,self.workspace,bool(i),size,self.follow.get())
            photo=ImageTk.PhotoImage(picture);self.photos.append(photo)
            canvas.delete('all');canvas.create_image(0,0,anchor='nw',image=photo)
        if self.workspace.last_error:self.status.set(self.workspace.last_error)
        self.root.after(50,self.tick)
    def close(self):
        self.closing=True
        self.worker.stopping=True;self.send('stop')
        self.status.set('Native Werkstatt-Laufzeit wird beendet …')
        def finish():
            if self.worker.is_alive():self.root.after(50,finish)
            else:self.root.destroy()
        finish()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',type=Path)
    parser.add_argument('--build',type=Path)
    parser.add_argument('--workspace',type=Path,default=DEFAULT_WORKSPACE)
    args=parser.parse_args()
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError,OSError):pass
    root=tk.Tk();Workshop(root,args.rom,args.build,args.workspace);root.mainloop()

if __name__=='__main__':main()
