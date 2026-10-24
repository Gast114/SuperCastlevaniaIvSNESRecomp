"""Visual Castlevania IV room editor with native playtests and separate projects."""
import argparse
import copy
import json
from pathlib import Path
import queue
import tempfile
import threading
import uuid
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from PIL import Image,ImageDraw,ImageTk
from level_project import Project,paint,room
from level_tiles import EMPTY,bind,resolve,sources,SOURCE_COUNT,source_name
from level_assets import Assets,ensure_room,ensure_source,collision_value
from level_playtest import Playtest
from enemy_workshop_native import NativeSession,ROOT
from monster_model import definitions


class Editor:
    def __init__(self,root,project=None):
        self.root=root;self.project=project or Project();self.room_id=self.project.data['rooms'][0]['id']
        self.assets={};self.events=queue.Queue();self.workers=[];self.playtest=None;self.closing=False;self.render_pending=False;self.play_pending=False;self.generation=0;self.tick_id=None;self.draw_id=None
        self.brush=[EMPTY];self.brush_collision=[0];self.brush_width=1;self.selection=None;self.selected_object=None;self.start=None;self.drag=None;self.clipboard=None
        self.loading_assets=set();self.failed_assets=set();self.empty_tile=Image.new('RGBA',(8,8));self.missing_tile=Image.new('RGBA',(8,8),'#74596d')
        self.zoom=tk.DoubleVar(value=2);self.layer=tk.StringVar(value='front');self.tool=tk.StringVar(value='Zeichnen')
        self.show_back=tk.BooleanVar(value=True);self.show_front=tk.BooleanVar(value=True);self.show_collision=tk.BooleanVar(value=False)
        self.auto_collision=tk.BooleanVar(value=True);self.grid=tk.BooleanVar(value=True);self.collision=tk.IntVar(value=1);self.palette=tk.IntVar(value=2)
        self.status=tk.StringVar(value='Grafiksatz wird vorbereitet …');self.origin_room=tk.IntVar(value=0);self.filter=tk.StringVar()
        self.source_room=tk.IntVar(value=self.current()['tileset']);self.source_layer=tk.StringVar(value='front')
        self.source_choice=tk.StringVar(value=f'{self.source_room.get()} · {source_name(self.source_room.get())}')
        self.name=tk.StringVar();self.width=tk.IntVar();self.height=tk.IntVar();self.collision_mode=tk.StringVar();self.props={k:tk.StringVar() for k in ('x','y','variant','target_x','target_y','target','trigger','plane')}
        self.ui=max(1.,min(1.7,root.winfo_screenwidth()/1920));root.tk.call('tk','scaling',96/72*self.ui)
        root.title('Castlevania IV · Level-Editor');root.geometry(f'{min(round(1680*self.ui),root.winfo_screenwidth()-80)}x{min(round(1020*self.ui),root.winfo_screenheight()-100)}')
        root.minsize(round(1080*self.ui),round(680*self.ui));style=ttk.Style();style.configure('.',font=('Segoe UI',11));style.configure('Treeview',rowheight=round(28*self.ui))
        toolbar=ttk.Frame(root,padding=8);toolbar.pack(fill='x')
        for text,fn in [('Neu',self.new),('Öffnen',self.open),('Speichern',self.save),('Speichern unter',lambda:self.save(True)),('↶ Rückgängig',self.undo),('↷ Wiederholen',self.redo),('▶ Spieltest',self.test),('■ Test beenden',self.stop_test)]:ttk.Button(toolbar,text=text,command=fn).pack(side='left',padx=3)
        controls=ttk.Frame(root,padding=(8,0));controls.pack(fill='x')
        for text in ('Auswahl','Zeichnen','Fläche','Kollision','Monster','Start','Ausgang'):ttk.Radiobutton(controls,text=text,variable=self.tool,value=text).pack(side='left',padx=3)
        ttk.Label(controls,text='Zielebene').pack(side='left',padx=(12,3));box=ttk.Combobox(controls,textvariable=self.layer,values=('front','back'),state='readonly',width=7);box.pack(side='left');box.bind('<<ComboboxSelected>>',lambda e:self.palette_changed())
        ttk.Label(controls,text='Zoom').pack(side='left',padx=(12,3));z=ttk.Combobox(controls,textvariable=self.zoom,values=(.5,1,2,3,4),state='readonly',width=4);z.pack(side='left');z.bind('<<ComboboxSelected>>',lambda e:self.schedule())
        options=ttk.Frame(root,padding=8);options.pack(fill='x')
        for text,var in [('Vordergrund',self.show_front),('Hintergrund',self.show_back),('Kollision anzeigen',self.show_collision),('Raster',self.grid)]:ttk.Checkbutton(options,text=text,variable=var,command=self.schedule).pack(side='left',padx=5)
        ttk.Checkbutton(options,text='Kollision beim Zeichnen übernehmen',variable=self.auto_collision).pack(side='left',padx=8)
        ttk.Radiobutton(options,text='Fest',variable=self.collision,value=1).pack(side='left');ttk.Radiobutton(options,text='Frei',variable=self.collision,value=0).pack(side='left')
        ttk.Label(options,text='Kachelpalette').pack(side='left',padx=(10,3));self.palette_box=ttk.Combobox(options,textvariable=self.palette,values=tuple(range(8)),state='readonly',width=3);self.palette_box.pack(side='left');self.palette_box.bind('<<ComboboxSelected>>',lambda e:self.palette_changed())
        panes=ttk.Panedwindow(root,orient='horizontal');panes.pack(fill='both',expand=True,padx=8)
        left=ttk.Frame(panes,width=230);center=ttk.Frame(panes);right=ttk.Frame(panes,width=330)
        panes.add(left,weight=0);panes.add(center,weight=1);panes.add(right,weight=0)
        ttk.Label(left,text='Räume',font=('Segoe UI',14,'bold')).pack(anchor='w')
        self.rooms=ttk.Treeview(left,show='tree',height=9);self.rooms.pack(fill='both',expand=True);self.rooms.bind('<<TreeviewSelect>>',self.choose_room)
        for text,fn in [('Neuer Raum',self.add_room),('Raum duplizieren',lambda:self.add_room(True)),('Als Startraum',self.set_start)]:ttk.Button(left,text=text,command=fn).pack(fill='x',pady=2)
        ttk.Label(left,text='Originalkarte: Abschnitt 0–67').pack(anchor='w',pady=(10,2));ttk.Spinbox(left,from_=0,to=67,textvariable=self.origin_room,width=8).pack(fill='x')
        ttk.Button(left,text='Originalkarte importieren',command=self.import_original).pack(fill='x',pady=3)
        ttk.Label(left,text='Raumeigenschaften').pack(anchor='w',pady=(12,3))
        for text,var in [('Name',self.name),('Breite in Pixeln',self.width),('Höhe in Pixeln',self.height)]:ttk.Label(left,text=text).pack(anchor='w');ttk.Entry(left,textvariable=var).pack(fill='x')
        ttk.Label(left,text='Kollision / Spielebenen').pack(anchor='w');ttk.Combobox(left,textvariable=self.collision_mode,state='readonly',values=('0 · Vordergrund','1 · Beide gemeinsam','2 · Vordergrund (nativ)','3 · Zwei Spielebenen'),width=24).pack(fill='x')
        ttk.Button(left,text='Raumwerte übernehmen',command=self.apply_room).pack(fill='x',pady=4)
        self.canvas=tk.Canvas(center,bg='#171d27',highlightthickness=0)
        sx=ttk.Scrollbar(center,orient='horizontal',command=lambda *a:self.scroll('x',*a));sy=ttk.Scrollbar(center,command=lambda *a:self.scroll('y',*a))
        self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set);sy.pack(side='right',fill='y');sx.pack(side='bottom',fill='x');self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.schedule());self.canvas.bind('<Button-1>',self.press);self.canvas.bind('<B1-Motion>',self.motion);self.canvas.bind('<ButtonRelease-1>',self.release);self.canvas.bind('<Button-3>',self.pick)
        self.canvas.bind('<MouseWheel>',self.wheel);self.canvas.bind('<Button-2>',lambda e:self.canvas.scan_mark(e.x,e.y));self.canvas.bind('<B2-Motion>',self.pan)
        source_box=ttk.LabelFrame(right,text='Grafiken aus allen Abschnitten',padding=6);source_box.pack(fill='x',pady=(0,5))
        ttk.Label(source_box,text='Quelle').grid(row=0,column=0,sticky='w');self.source_picker=ttk.Combobox(source_box,textvariable=self.source_choice,values=tuple(f'{n} · {source_name(n)}' for n in range(SOURCE_COUNT)),width=18,state='readonly');self.source_picker.grid(row=0,column=1,sticky='ew');self.source_picker.bind('<<ComboboxSelected>>',self.source_changed)
        source_layer=ttk.Combobox(source_box,textvariable=self.source_layer,values=('front','back'),width=7,state='readonly');source_layer.grid(row=0,column=2,padx=4);source_layer.bind('<<ComboboxSelected>>',self.source_changed)
        ttk.Label(source_box,text='Quelle frei wählen, dann in jede Zielebene zeichnen.',wraplength=round(300*self.ui)).grid(row=1,column=0,columnspan=3,sticky='w')
        ttk.Button(source_box,text='Alle Grafikquellen vorbereiten',command=lambda:self.load_assets(range(SOURCE_COUNT))).grid(row=2,column=0,columnspan=3,sticky='ew',pady=(4,0))
        self.tabs=ttk.Notebook(right);self.tabs.pack(fill='both',expand=True)
        self.block_canvas=self.palette_canvas('Blöcke 32px');self.tile_canvas=self.palette_canvas('Kacheln 8px')
        self.block_canvas.bind('<Button-1>',self.choose_block);self.tile_canvas.bind('<Button-1>',self.choose_tile)
        monsters=ttk.Frame(self.tabs);self.tabs.add(monsters,text='Monster')
        ttk.Entry(monsters,textvariable=self.filter).pack(fill='x');self.filter.trace_add('write',lambda *a:self.filter_monsters())
        self.monsters=ttk.Treeview(monsters,show='tree');self.monsters.pack(fill='both',expand=True);self.monsters.bind('<<TreeviewSelect>>',lambda e:self.tool.set('Monster'))
        ttk.Label(monsters,text='Bosse sind zunächst Planungsmarker.\nSpieltest-Spezialadapter folgen.',wraplength=290).pack(anchor='w',pady=5)
        props=ttk.LabelFrame(right,text='Auswahl / Ausgang',padding=7);props.pack(fill='x',pady=6)
        for n,(label,key) in enumerate([('X','x'),('Y','y'),('Variante','variant'),('Zielraum','target'),('Ziel X','target_x'),('Ziel Y','target_y'),('Auslöser','trigger'),('Ebene / Zielebene','plane')]):
            ttk.Label(props,text=label).grid(row=n,column=0,sticky='w')
            if key in ('target','trigger','plane'):
                control=ttk.Combobox(props,textvariable=self.props[key],width=20,state='readonly',values=('up','touch') if key=='trigger' else ('front','back') if key=='plane' else ())
                if key=='target':self.target_box=control
            else:control=ttk.Entry(props,textvariable=self.props[key],width=16)
            control.grid(row=n,column=1,sticky='ew')
        ttk.Button(props,text='Übernehmen',command=self.apply_object).grid(row=8,column=0,sticky='ew',pady=5);ttk.Button(props,text='Löschen',command=self.delete).grid(row=8,column=1,sticky='ew')
        ttk.Label(root,textvariable=self.status,padding=8,wraplength=1500).pack(fill='x')
        for key,fn in [('<Control-s>',self.save),('<Control-o>',self.open),('<Control-n>',self.new),('<Control-z>',self.undo),('<Control-y>',self.redo),('<F5>',self.test)]:root.bind(key,lambda e,f=fn:f())
        for key,fn in [('<Control-c>',self.copy),('<Control-v>',self.paste),('<Delete>',self.delete)]:self.canvas.bind(key,lambda e,f=fn:f())
        self.canvas.bind('<h>',lambda e:self.flip(True));self.canvas.bind('<v>',lambda e:self.flip(False));root.protocol('WM_DELETE_WINDOW',self.close)
        raw=NativeSession.__new__(NativeSession);raw.bytes=(ROOT/'Super Castlevania IV (USA).sfc').read_bytes();catalog=raw.read_catalog()
        from enemy_catalog_profiles import boss_profiles
        self.catalog=catalog+boss_profiles(raw);self.definitions=definitions(self.catalog,raw.bytes);self.filter_monsters()
        self.refresh_rooms();self.load_asset(self.source_room.get());self.tick_id=root.after(60,self.tick)

    def current(self):return self.project.get(self.room_id)
    def palette_canvas(self,title):
        f=ttk.Frame(self.tabs);self.tabs.add(f,text=title);c=tk.Canvas(f,bg='#252c38',width=290,height=350,highlightthickness=0)
        bar=ttk.Scrollbar(f,command=c.yview);bar.pack(side='right',fill='y');c.configure(yscrollcommand=bar.set);c.pack(fill='both',expand=True)
        c.bind('<MouseWheel>',lambda e:c.yview_scroll(-int(e.delta/120)*3,'units'));return c
    def background(self,fn):
        def work():
            try:
                result=fn()
                if self.closing and result[0]=='play':result[1].close()
                else:self.events.put(('ok',result))
            except Exception as e:self.events.put(('error',str(e)))
        t=threading.Thread(target=work,daemon=True);self.workers.append(t);t.start()
    def load_asset(self,n):
        self.load_assets([n])
    def load_assets(self,numbers):
        missing=sorted(set(numbers)-self.assets.keys()-self.loading_assets-self.failed_assets)
        if not missing:self.palette_changed();return
        self.loading_assets.update(missing);self.status.set('Grafikquellen werden einmalig vorbereitet: '+', '.join(source_name(n) for n in missing))
        def prepare():
            for n in missing:
                if self.closing:break
                try:self.events.put(('ok',('assets',[(n,ensure_source(n))],[])))
                except Exception as exc:self.events.put(('ok',('assets',[],[(n,str(exc))])))
            return 'sources_done',
        self.background(prepare)
    def source_changed(self,e=None):
        if e and e.widget==self.source_picker:self.source_room.set(int(self.source_choice.get().split(' · ')[0]))
        self.source_choice.set(f'{self.source_room.get()} · {source_name(self.source_room.get())}')
        n=self.source_room.get();self.failed_assets.discard(n);self.load_asset(n)
    def tile_image(self,value,default_source,default_layer):
        ref=resolve(value,default_source,default_layer)
        if ref is None:return self.empty_tile
        n,layer,word=ref;asset=self.assets.get(n)
        return asset.tile(word,layer) if asset else self.missing_tile
    def tile_collision(self,value,default_source,default_layer):
        ref=resolve(value,default_source,default_layer)
        if ref is None:return 0
        n,_,word=ref;asset=self.assets.get(n)
        if not asset or asset.meta['ppu']['bgmode']&7==7:return 0
        return collision_value(word,asset.meta['limits'])
    def tick(self):
        self.tick_id=None
        if self.closing:return
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='error':self.play_pending=False;self.status.set(value);messagebox.showerror('Level-Editor',value,parent=self.root)
                elif value[0]=='assets':
                    for n,path in value[1]:self.loading_assets.discard(n);self.assets[n]=Assets(path)
                    for n,error in value[2]:self.loading_assets.discard(n);self.failed_assets.add(n)
                    if any(n==self.source_room.get() for n,path in value[1]):self.palette_changed()
                    else:self.schedule()
                    if value[2]:self.status.set(' · '.join(f'{source_name(n)}: {error}' for n,error in value[2]))
                elif value[0]=='sources_done' and not self.loading_assets and not self.failed_assets:
                    self.status.set('Grafikquellen bereit · Quelle und Zielebene frei kombinieren · F5 testen'+(' · '+self.current()['source_note'] if self.current().get('source_note') else ''))
                elif value[0]=='import':
                    if value[2]!=self.generation:continue
                    self.project.begin('Originalkarte importieren');r=value[1];self.project.data['rooms'].append(r);self.project.commit();self.room_id=r['id'];self.refresh_rooms();self.load_asset(r['tileset'])
                elif value[0]=='play':
                    self.play_pending=False;self.playtest=value[1];self.playtest.session.lua.command('resume');self.status.set('Spieltest läuft in einem separaten Fenster'+(' ohne Ton (kein Audiogerät)' if self.playtest.audio_unavailable else '')+'. Mit „Test beenden“ schließen.')
        except queue.Empty:pass
        self.tick_id=self.root.after(60,self.tick)
    def refresh_rooms(self):
        self.rooms.delete(*self.rooms.get_children())
        if not any(r['id']==self.room_id for r in self.project.data['rooms']):self.room_id=self.project.data['rooms'][0]['id']
        for r in self.project.data['rooms']:self.rooms.insert('','end',iid=r['id'],text=('★ ' if r['id']==self.project.data['start_room'] else '')+r['name'])
        self.target_box.configure(values=tuple(r['id']+' · '+r['name'] for r in self.project.data['rooms']))
        self.rooms.selection_set(self.room_id);self.update_room();self.load_assets(sources(self.current()));self.schedule()
    def choose_room(self,e=None):
        if self.rooms.selection():self.room_id=self.rooms.selection()[0];self.selected_object=None;self.selection=None;self.update_room();self.load_assets(sources(self.current()));self.schedule()
    def update_room(self):
        r=self.current();self.name.set(r['name']);self.width.set(r['width']*8);self.height.set(r['height']*8);self.collision_mode.set(('0 · Vordergrund','1 · Beide gemeinsam','2 · Vordergrund (nativ)','3 · Zwei Spielebenen')[r.get('collision_mode',0)])
    def add_room(self,duplicate=False):
        source=self.current();r=self.project.add_room(source if duplicate else None,tileset=source['tileset'])
        self.room_id=r['id'];self.refresh_rooms();self.load_asset(r['tileset'])
    def set_start(self):self.project.begin('Startraum');self.project.data['start_room']=self.room_id;self.project.commit();self.refresh_rooms()
    def apply_room(self):
        try:
            width,height=self.width.get(),self.height.get()
            if width%8 or height%8:raise ValueError('Breite und Höhe müssen durch 8 teilbar sein.')
            r=self.current();self.project.resize(r,width//8,height//8,name=self.name.get().strip() or r['id'],collision_mode=int(self.collision_mode.get()[0]));self.refresh_rooms()
        except Exception as e:messagebox.showerror('Raum',str(e),parent=self.root)
    def import_original(self):
        n=self.origin_room.get();generation=self.generation
        self.status.set(f'Originalkarte R-{n:02d} wird eingelesen …');self.background(lambda:('import',Assets(ensure_room(n)).import_room(),generation))
    def scroll(self,axis,*args):getattr(self.canvas,axis+'view')(*args);self.schedule()
    def pan(self,e):self.canvas.scan_dragto(e.x,e.y,gain=1);self.schedule()
    def wheel(self,e):
        if e.state&4:self.zoom.set(max(.5,min(4,self.zoom.get()+(.5 if e.delta>0 else -.5))))
        else:getattr(self.canvas,'xview_scroll' if e.state&1 else 'yview_scroll')(-int(e.delta/120)*3,'units')
        self.schedule()
    def schedule(self):
        if self.closing:return
        if not self.render_pending:self.render_pending=True;self.draw_id=self.root.after(30,self.draw)
    def draw(self):
        self.render_pending=False;self.draw_id=None
        if self.closing:return
        r=self.current();z=self.zoom.get();self.canvas.configure(scrollregion=(0,0,r['width']*8*z,r['height']*8*z))
        x0=max(0,int(self.canvas.canvasx(0)/z)//8);y0=max(0,int(self.canvas.canvasy(0)/z)//8)
        nx=min(r['width']-x0,int(self.canvas.winfo_width()/z/8)+2);ny=min(r['height']-y0,int(self.canvas.winfo_height()/z/8)+2)
        if nx<=0 or ny<=0:return
        image=Image.new('RGBA',(nx*8,ny*8),'#202632')
        for layer,shown in [('back',self.show_back.get()),('front',self.show_front.get())]:
            if shown:
                for yy in range(ny):
                    for xx in range(nx):image.alpha_composite(self.tile_image(r['layers'][layer][(y0+yy)*r['width']+x0+xx],r['tileset'],layer),(xx*8,yy*8))
        if self.show_collision.get():
            d=ImageDraw.Draw(image,'RGBA')
            for yy in range(ny):
                for xx in range(nx):
                    v=r['collision'][self.layer.get()][(y0+yy)*r['width']+x0+xx]
                    if v:d.rectangle((xx*8,yy*8,xx*8+7,yy*8+7),fill=(255,90,65,105) if v==1 else (240,190,30,110))
        image=image.resize((max(1,round(image.width*z)),max(1,round(image.height*z))),Image.Resampling.NEAREST)
        self.photo=ImageTk.PhotoImage(image);self.canvas.delete('all');self.canvas.create_image(x0*8*z,y0*8*z,image=self.photo,anchor='nw')
        if self.grid.get() and z>=1:
            for x in range((x0//4)*4,x0+nx+1,4):self.canvas.create_line(x*8*z,y0*8*z,x*8*z,(y0+ny)*8*z,fill='#394658')
            for y in range((y0//4)*4,y0+ny+1,4):self.canvas.create_line(x0*8*z,y*8*z,(x0+nx)*8*z,y*8*z,fill='#394658')
        for a in r['actors']:
            x,y=a['x']*z,a['y']*z;self.canvas.create_rectangle(x-10*z,y-16*z,x+10*z,y+16*z,outline='#e8ae64' if a['type']>=128 else '#94d76c',width=2)
            self.canvas.create_text(x,y-21*z,text=f'M-{a["type"]:04X}',fill='#eff4ed',anchor='s',font=('Segoe UI',10))
        for d in r['doors']:
            self.canvas.create_rectangle(d['x']*z,d['y']*z,(d['x']+d['w'])*z,(d['y']+d['h'])*z,outline='#7ebeff',width=3)
            self.canvas.create_text(d['x']*z,d['y']*z,text='→ '+d['target'],anchor='sw',fill='#9bd0ff')
        x,y=r['spawn'];self.canvas.create_oval((x-6)*z,(y-6)*z,(x+6)*z,(y+6)*z,fill='#63cde5',outline='white');self.canvas.create_text(x*z,(y-10)*z,text='START',fill='#9eeaff',anchor='s')
        if self.selection:
            x1,y1,x2,y2=self.selection;self.canvas.create_rectangle(x1*8*z,y1*8*z,(x2+1)*8*z,(y2+1)*8*z,outline='#f6e58d',dash=(5,3),width=2)
        self.root.title(('● ' if self.project.dirty else '')+'Castlevania IV · '+self.project.data['name'])
    def palette_changed(self):
        asset=self.assets.get(self.source_room.get())
        if not asset:return
        source_layer=self.source_layer.get();height=asset.block_count//8*32;self.palette_box.configure(state='disabled' if asset.meta['ppu']['bgmode']&7==7 else 'readonly')
        image=Image.new('RGBA',(256,height),'#252c38')
        for n in range(asset.block_count):
            for i,w in enumerate(asset.block(n,source_layer)):image.alpha_composite(asset.tile(w,source_layer),((n%8)*32+(i%4)*8,(n//8)*32+(i//4)*8))
        self.block_photo=ImageTk.PhotoImage(image.resize((round(256*self.ui),round(height*self.ui)),Image.Resampling.NEAREST));self.block_canvas.delete('all');self.block_canvas.create_image(0,0,image=self.block_photo,anchor='nw');self.block_canvas.configure(scrollregion=(0,0,256*self.ui,height*self.ui))
        height=asset.tile_count//16*20;image=Image.new('RGBA',(320,height),'#252c38')
        for n in range(asset.tile_count):image.alpha_composite(asset.tile(n|(self.palette.get()<<10),source_layer).resize((20,20),Image.Resampling.NEAREST),((n%16)*20,(n//16)*20))
        self.tile_photo=ImageTk.PhotoImage(image.resize((round(320*self.ui),round(height*self.ui)),Image.Resampling.NEAREST));self.tile_canvas.delete('all');self.tile_canvas.create_image(0,0,image=self.tile_photo,anchor='nw');self.tile_canvas.configure(scrollregion=(0,0,320*self.ui,height*self.ui))
        self.status.set(self.current().get('source_note') or 'Bereit · Linksklick zeichnen · Rechtsklick aufnehmen · Mitteltaste verschieben · Strg+Mausrad zoomen · H/V spiegeln · F5 testen');self.schedule()
    def choose_block(self,e):
        asset=self.assets.get(self.source_room.get())
        if not asset:return
        x,y=self.block_canvas.canvasx(e.x)/self.ui,self.block_canvas.canvasy(e.y)/self.ui;n=int(y//32)*8+int(x//32)
        if not 0<=n<asset.block_count:return
        self.brush=[bind(w,self.source_room.get(),self.source_layer.get()) for w in asset.block(n,self.source_layer.get())];self.brush_width=4;self.recollision();self.tool.set('Zeichnen');self.status.set(f'Quelle {source_name(self.source_room.get())} / {self.source_layer.get()} · Block {n:03X} · 32 × 32 Pixel')
    def choose_tile(self,e):
        asset=self.assets.get(self.source_room.get())
        if not asset:return
        x,y=self.tile_canvas.canvasx(e.x)/self.ui,self.tile_canvas.canvasy(e.y)/self.ui;n=int(y//20)*16+int(x//20)
        if not 0<=n<asset.tile_count:return
        self.brush=[bind(n|(self.palette.get()<<10),self.source_room.get(),self.source_layer.get())];self.brush_width=1;self.recollision();self.tool.set('Zeichnen');self.status.set(f'Quelle {source_name(self.source_room.get())} / {self.source_layer.get()} · Kachel {n:03X} · 8 × 8 Pixel')
    def recollision(self):self.brush_collision=[self.tile_collision(w,self.current()['tileset'],self.layer.get()) for w in self.brush]
    def filter_monsters(self):
        self.monsters.delete(*self.monsters.get_children());term=self.filter.get().casefold()
        for m in self.definitions:
            label=m['code']+(' · Boss / Planung' if m['boss'] else '')
            if term in label.casefold():self.monsters.insert('','end',iid=m['code'],text=label)
    def coords(self,e):return int(self.canvas.canvasx(e.x)/(8*self.zoom.get())),int(self.canvas.canvasy(e.y)/(8*self.zoom.get()))
    def press(self,e):
        self.canvas.focus_set()
        r=self.current();x,y=self.coords(e)
        if not 0<=x<r['width'] or not 0<=y<r['height']:return
        self.start=(x,y);self.drag=(x,y);self.project.begin(self.tool.get());tool=self.tool.get()
        if tool!='Auswahl':self.selected_object=None
        if tool=='Auswahl':
            self.selected_object=None
            for kind,rows in [('actor',r['actors']),('door',r['doors'])]:
                for item in reversed(rows):
                    if abs(item['x']-x*8)<24 and abs(item['y']-y*8)<24:self.selected_object=(kind,item['id']);break
                if self.selected_object:break
            if self.selected_object:self.object_fields()
            else:self.selection=(x,y,x,y)
        elif tool in ('Zeichnen','Kollision'):self.stamp(x,y)
        elif tool=='Fläche':self.selection=(x,y,x,y)
        elif tool=='Start':r['spawn']=[x*8,y*8]
        elif tool=='Monster':
            selected=self.monsters.selection()
            if selected:
                t=int(selected[0][2:],16);entry=next(e for e in self.catalog if e['type']==t)
                item=dict(id='E-'+uuid.uuid4().hex[:8],type=t,variant=entry['variant'],x=x*8,y=y*8,flags=(entry['flags']&0x7fff)|(0x8000 if self.layer.get()=='front' else 0))
                r['actors'].append(item);self.selected_object=('actor',item['id']);self.object_fields()
        elif tool=='Ausgang':
            target=next((q for q in self.project.data['rooms'] if q['id']!=r['id']),r)
            d=dict(id='D-'+uuid.uuid4().hex[:8],x=x*8,y=y*8,w=32,h=48,target=target['id'],target_x=target['spawn'][0],target_y=target['spawn'][1],trigger='up')
            r['doors'].append(d);self.selected_object=('door',d['id']);self.object_fields()
        self.schedule()
    def stamp(self,x,y):
        r=self.current();layer=self.layer.get()
        if self.tool.get()=='Kollision':
            if 0<=x<r['width'] and 0<=y<r['height']:r['collision'][layer][y*r['width']+x]=self.collision.get()
        else:
            w=self.brush_width;x=x//w*w;y=y//max(1,len(self.brush)//w)*max(1,len(self.brush)//w)
            paint(r,layer,x,y,self.brush,self.brush_collision if self.auto_collision.get() else None,w)
    def motion(self,e):
        if self.start is None:return
        x,y=self.coords(e);r=self.current();tool=self.tool.get()
        if tool in ('Zeichnen','Kollision'):
            ox,oy=self.drag;n=max(abs(x-ox),abs(y-oy),1)
            for i in range(n+1):self.stamp(round(ox+(x-ox)*i/n),round(oy+(y-oy)*i/n))
        elif tool in ('Fläche','Auswahl') and not self.selected_object:self.selection=(max(0,min(self.start[0],x)),max(0,min(self.start[1],y)),min(r['width']-1,max(self.start[0],x)),min(r['height']-1,max(self.start[1],y)))
        elif tool=='Auswahl' and self.selected_object:
            item=self.object();item['x']=max(0,min(r['width']*8-1,x*8));item['y']=max(0,min(r['height']*8-1,y*8));self.object_fields()
        self.drag=(x,y);self.schedule()
    def release(self,e):
        if self.start is None:return
        if self.tool.get()=='Fläche' and self.selection:
            x1,y1,x2,y2=self.selection;w=self.brush_width;h=max(1,len(self.brush)//w)
            for y in range(y1,y2+1,h):
                for x in range(x1,x2+1,w):paint(self.current(),self.layer.get(),x,y,self.brush,self.brush_collision if self.auto_collision.get() else None,w)
        self.project.commit();self.start=None;self.schedule()
    def pick(self,e):
        x,y=self.coords(e);r=self.current()
        if 0<=x<r['width'] and 0<=y<r['height']:
            self.brush=[bind(r['layers'][self.layer.get()][y*r['width']+x],r['tileset'],self.layer.get())];self.brush_collision=[r['collision'][self.layer.get()][y*r['width']+x]];self.brush_width=1;self.tool.set('Zeichnen');self.status.set(f'Kachel mit Originalquelle aufgenommen: {self.brush[0]:08X}')
    def object(self):
        if not self.selected_object:return None
        kind,identifier=self.selected_object;return next((a for a in self.current()['actors' if kind=='actor' else 'doors'] if a['id']==identifier),None)
    def object_fields(self):
        item=self.object()
        if item:
            for k,v in self.props.items():v.set(str(item.get(k,'')))
            self.props['plane'].set(('back' if item.get('flags',0)&0x8000==0 else 'front') if self.selected_object[0]=='actor' else ('back' if item.get('target_plane',0) else 'front'))
            if 'target' in item:
                target=self.project.get(item['target']);self.props['target'].set(target['id']+' · '+target['name'])
    def apply_object(self):
        item=self.object()
        if not item:return
        try:
            values={k:int(self.props[k].get()) for k in ('x','y')}
            if self.selected_object[0]=='actor':values.update(variant=int(self.props['variant'].get()),flags=(item.get('flags',0)&0x7fff)|(0x8000 if self.props['plane'].get()=='front' else 0))
            else:values.update(target=self.props['target'].get().split(' · ')[0],target_x=int(self.props['target_x'].get()),target_y=int(self.props['target_y'].get()),trigger=self.props['trigger'].get(),target_plane=int(self.props['plane'].get()=='back'))
            self.project.begin('Objektwerte');item.update(values)
            from level_project import validate
            validate(self.project.data);self.project.commit();self.schedule()
        except Exception as e:
            if self.project.transaction:self.project.data=self.project.transaction[1];self.project.transaction=None
            messagebox.showerror('Objekt',str(e),parent=self.root)
    def delete(self):
        self.project.begin('Löschen');r=self.current()
        if self.selected_object:
            kind,identifier=self.selected_object;key='actors' if kind=='actor' else 'doors';r[key]=[a for a in r[key] if a['id']!=identifier];self.selected_object=None
        elif self.selection:
            x1,y1,x2,y2=self.selection
            for y in range(y1,y2+1):
                for x in range(x1,x2+1):paint(r,self.layer.get(),x,y,[EMPTY],[0])
        self.project.commit();self.schedule()
    def copy(self):
        if not self.selection:return
        r=self.current();x1,y1,x2,y2=self.selection;w=x2-x1+1
        self.clipboard=([bind(r['layers'][self.layer.get()][y*r['width']+x],r['tileset'],self.layer.get()) for y in range(y1,y2+1) for x in range(x1,x2+1)],
                        [r['collision'][self.layer.get()][y*r['width']+x] for y in range(y1,y2+1) for x in range(x1,x2+1)],w)
        self.status.set(f'Ausschnitt {w*8} × {(y2-y1+1)*8} Pixel kopiert.')
    def paste(self):
        if self.clipboard:self.brush,self.brush_collision,self.brush_width=copy.deepcopy(self.clipboard);self.tool.set('Zeichnen');self.status.set('Ausschnitt mit Linksklick platzieren.')
    def flip(self,horizontal):
        w=self.brush_width;h=len(self.brush)//w;indices=[(y*w+(w-1-x) if horizontal else (h-1-y)*w+x) for y in range(h) for x in range(w)]
        values=[];collisions=[]
        for i in indices:
            old=self.brush[i];value=old^(0x4000 if horizontal else 0x8000) if old!=EMPTY else EMPTY
            collision=self.brush_collision[i]
            if collision==self.tile_collision(old,self.current()['tileset'],self.layer.get()):collision=self.tile_collision(value,self.current()['tileset'],self.layer.get())
            values.append(value);collisions.append(collision)
        self.brush,self.brush_collision=values,collisions
    def undo(self):self.project.undo();self.selected_object=None;self.refresh_rooms()
    def redo(self):self.project.redo();self.selected_object=None;self.refresh_rooms()
    def confirm(self):return not self.project.dirty or messagebox.askyesno('Ungespeicherte Änderungen','Ohne Speichern fortfahren?',parent=self.root)
    def new(self):
        if self.confirm():self.generation+=1;self.project=Project();self.room_id=self.project.data['rooms'][0]['id'];self.refresh_rooms();self.load_asset(0)
    def open(self):
        if not self.confirm():return
        name=filedialog.askopenfilename(parent=self.root,initialdir=self.project_directory(),filetypes=[('Castlevania-Level','*.sc4level.json'),('JSON','*.json')])
        if name:
            try:self.project=Project.load(name);self.generation+=1;self.room_id=self.project.data['start_room'];self.refresh_rooms();self.load_asset(self.current()['tileset'])
            except Exception as e:messagebox.showerror('Öffnen',str(e),parent=self.root)
    def save(self,as_new=False):
        name=self.project.path
        if as_new or name is None:name=filedialog.asksaveasfilename(parent=self.root,initialdir=self.project_directory(),defaultextension='.sc4level.json',initialfile='Mein_Level.sc4level.json',filetypes=[('Castlevania-Level','*.sc4level.json')])
        if name:
            try:self.project.save(name);self.status.set('Projekt gespeichert: '+str(name));self.schedule()
            except Exception as e:messagebox.showerror('Speichern',str(e),parent=self.root)
    def project_directory(self):
        path=self.project.path.parent if self.project.path else ROOT/'artwork-local/level-editor/projects';path.mkdir(parents=True,exist_ok=True);return path
    def test(self):
        if self.play_pending:return
        if self.playtest:self.stop_test()
        parent=ROOT/'artwork-local/level-editor/tests';parent.mkdir(parents=True,exist_ok=True);folder=Path(tempfile.mkdtemp(prefix='play-',dir=parent));data=copy.deepcopy(self.project.data)
        self.play_pending=True;scale=round(3*self.ui);self.status.set('Spieltest wird vorbereitet …');self.background(lambda:('play',Playtest(data,folder,window_scale=scale)))
    def stop_test(self):
        if self.playtest:self.playtest.close();self.playtest=None;self.status.set('Spieltest beendet. Dein Projekt bleibt geöffnet.')
    def close(self):
        if not self.confirm():return
        self.closing=True
        for timer in (self.tick_id,self.draw_id):
            if timer:self.root.after_cancel(timer)
        self.stop_test();self.root.withdraw();self.finish_close()
    def finish_close(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='ok' and value[0]=='play':value[1].close()
        except queue.Empty:pass
        if any(t.is_alive() for t in self.workers):self.root.after(100,self.finish_close)
        else:self.root.destroy()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',type=Path);parser.add_argument('--demo',action='store_true');args=parser.parse_args()
    if args.demo and args.project is None:
        from level_demo import make_demo
        args.project=make_demo()
    root=tk.Tk();Editor(root,Project.load(args.project) if args.project else None);root.mainloop()
