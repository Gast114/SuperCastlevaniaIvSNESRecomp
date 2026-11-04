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
from level_parts import CATEGORIES,builtin_parts,repeat_part,capture_part,validate_part,pick_connected_part
from level_playtest import Playtest,OriginalPlaytest
from enemy_workshop_native import NativeSession,ROOT
from monster_model import definitions,ai_notes
from level_actor_values import LIMITS,values_for
from level_objects import SpriteLibrary,MOVING_PLATFORMS,is_platform,platform_path,validate_platform,scene_objects


class Editor:
    def __init__(self,root,project=None):
        self.root=root;self.project=project or Project();self.room_id=self.project.data['rooms'][0]['id']
        self.original_view=project is None;self.original_room=None;self.original_number=0;self.original_loading=False;self.original_error='';self.original_cache={}
        self.assets={};self.events=queue.Queue();self.workers=[];self.playtest=None;self.closing=False;self.render_pending=False;self.play_pending=False;self.generation=0;self.tick_id=None;self.draw_id=None
        self.brush=[EMPTY];self.brush_collision=[0];self.brush_width=1;self.selection=None;self.selected_object=None;self.start=None;self.drag=None;self.clipboard=None
        self.brush_mask=None;self.hover=None;self.parts={};self.part_photos=[]
        self.sprites=SpriteLibrary(ROOT/'artwork-local/enemy-library');self.object_template=None;self.object_rows={};self.monster_photos=[];self.object_photos=[];self.object_types=set()
        self.part_category=tk.StringVar(value='Alle');self.part_length=tk.IntVar(value=4);self.part_name=tk.StringVar(value='Mein Bauteil');self.brush_label=tk.StringVar(value='Bauteil auswählen oder eine Auswahl merken.')
        self.loading_assets=set();self.failed_assets=set();self.empty_tile=Image.new('RGBA',(8,8));self.missing_tile=Image.new('RGBA',(8,8),'#74596d')
        self.zoom=tk.DoubleVar(value=2);self.layer=tk.StringVar(value='front');self.tool=tk.StringVar(value='Zeichnen')
        self.show_back=tk.BooleanVar(value=True);self.show_front=tk.BooleanVar(value=True);self.show_collision=tk.BooleanVar(value=False)
        self.show_object_names=tk.BooleanVar(value=True)
        self.actor_stats=tk.StringVar();self.stats_window=None;self.stat_fields={}
        self.auto_collision=tk.BooleanVar(value=True);self.grid=tk.BooleanVar(value=True);self.collision=tk.IntVar(value=1);self.palette=tk.IntVar(value=2)
        self.status=tk.StringVar(value='Grafiksatz wird vorbereitet …');self.origin_room=tk.IntVar(value=0);self.filter=tk.StringVar()
        self.source_room=tk.IntVar(value=self.current()['tileset']);self.source_layer=tk.StringVar(value='front')
        self.source_choice=tk.StringVar(value=f'{self.source_room.get()} · {source_name(self.source_room.get())}')
        self.name=tk.StringVar();self.width=tk.IntVar();self.height=tk.IntVar();self.collision_mode=tk.StringVar();self.props={k:tk.StringVar() for k in ('x','y','variant','target_x','target_y','target','trigger','plane','motion','name')}
        self.ui=max(1.,min(1.7,root.winfo_screenwidth()/1920));root.tk.call('tk','scaling',96/72*self.ui)
        root.title('Castlevania IV · Level-Editor');root.geometry(f'{min(round(1680*self.ui),root.winfo_screenwidth()-80)}x{min(round(1020*self.ui),root.winfo_screenheight()-100)}')
        root.minsize(round(1080*self.ui),round(680*self.ui));style=ttk.Style();style.configure('.',font=('Segoe UI',11));style.configure('Treeview',rowheight=round(28*self.ui))
        toolbar=ttk.Frame(root,padding=8);toolbar.pack(fill='x')
        for text,fn in [('Neu',self.new),('Öffnen',self.open),('Speichern',self.save),('Speichern unter',lambda:self.save(True)),('↶ Rückgängig',self.undo),('↷ Wiederholen',self.redo),('▶ Spieltest',self.test),('■ Test beenden',self.stop_test)]:ttk.Button(toolbar,text=text,command=fn).pack(side='left',padx=3)
        controls=ttk.Frame(root,padding=(8,0));controls.pack(fill='x')
        for text in ('Auswahl','Bauteil','Zeichnen','Fläche','Kollision','Monster','Objekt','Start','Ausgang'):ttk.Radiobutton(controls,text=text,variable=self.tool,value=text).pack(side='left',padx=3)
        ttk.Label(controls,text='Zielebene').pack(side='left',padx=(12,3));box=ttk.Combobox(controls,textvariable=self.layer,values=('front','back'),state='readonly',width=7);box.pack(side='left');box.bind('<<ComboboxSelected>>',lambda e:self.palette_changed())
        ttk.Label(controls,text='Zoom').pack(side='left',padx=(12,3));z=ttk.Combobox(controls,textvariable=self.zoom,values=(.5,1,2,3,4),state='readonly',width=4);z.pack(side='left');z.bind('<<ComboboxSelected>>',lambda e:self.schedule())
        options=ttk.Frame(root,padding=8);options.pack(fill='x')
        for text,var in [('Vordergrund',self.show_front),('Hintergrund',self.show_back),('Kollision anzeigen',self.show_collision),('Raster',self.grid),('Objektnamen',self.show_object_names)]:ttk.Checkbutton(options,text=text,variable=var,command=self.schedule).pack(side='left',padx=5)
        ttk.Checkbutton(options,text='Kollision beim Zeichnen übernehmen',variable=self.auto_collision).pack(side='left',padx=8)
        ttk.Radiobutton(options,text='Fest',variable=self.collision,value=1).pack(side='left');ttk.Radiobutton(options,text='Frei',variable=self.collision,value=0).pack(side='left')
        ttk.Label(options,text='Kachelpalette').pack(side='left',padx=(10,3));self.palette_box=ttk.Combobox(options,textvariable=self.palette,values=tuple(range(8)),state='readonly',width=3);self.palette_box.pack(side='left');self.palette_box.bind('<<ComboboxSelected>>',lambda e:self.palette_changed())
        panes=ttk.Panedwindow(root,orient='horizontal');panes.pack(fill='both',expand=True,padx=8)
        left=ttk.Frame(panes,width=230);center=ttk.Frame(panes);right=ttk.Frame(panes,width=330)
        panes.add(left,weight=0);panes.add(center,weight=1);panes.add(right,weight=0)
        ttk.Label(left,text='Originalspiel / eigenes Projekt',font=('Segoe UI',12,'bold')).pack(anchor='w')
        self.room_tabs=ttk.Notebook(left);self.room_tabs.pack(fill='both',expand=True)
        self.original_tab=ttk.Frame(self.room_tabs);self.project_tab=ttk.Frame(self.room_tabs);self.room_tabs.add(self.original_tab,text='Originalspiel');self.room_tabs.add(self.project_tab,text='Mein Projekt')
        original_list=ttk.Frame(self.original_tab);original_list.pack(fill='both',expand=True)
        original_scroll=ttk.Scrollbar(original_list);original_scroll.pack(side='right',fill='y')
        self.originals=ttk.Treeview(original_list,show='tree',height=9,selectmode='browse',yscrollcommand=original_scroll.set);original_scroll.configure(command=self.originals.yview);self.originals.pack(fill='both',expand=True)
        for n in range(68):self.originals.insert('','end',iid=str(n),text=f'R-{n:02d}'+(f' · Stage 01 / A{n+1:02d}' if n<5 else ''))
        self.originals.bind('<<TreeviewSelect>>',self.choose_original)
        self.copy_original_button=ttk.Button(self.original_tab,text='Als eigene Kopie bearbeiten',command=self.edit_original,state='disabled');self.copy_original_button.pack(fill='x',pady=3)
        ttk.Button(self.original_tab,text='Neues eigenes Level',command=self.new).pack(fill='x',pady=3)
        self.rooms=ttk.Treeview(self.project_tab,show='tree',height=9);self.rooms.pack(fill='both',expand=True);self.rooms.bind('<<TreeviewSelect>>',self.choose_room)
        self.room_tabs.select(self.original_tab if self.original_view else self.project_tab);self.room_tabs.bind('<<NotebookTabChanged>>',self.room_tab_changed)
        self.room_controls=ttk.Frame(left);self.room_controls.pack(side='bottom',fill='x',before=self.room_tabs)
        for text,fn in [('Neuer Raum',self.add_room),('Raum duplizieren',lambda:self.add_room(True)),('Als Startraum',self.set_start)]:ttk.Button(self.room_controls,text=text,command=fn).pack(fill='x',pady=2)
        ttk.Label(self.room_controls,text='Weiteren Originalabschnitt hinzufügen: 0–67').pack(anchor='w',pady=(10,2));ttk.Spinbox(self.room_controls,from_=0,to=67,textvariable=self.origin_room,width=8).pack(fill='x')
        ttk.Button(self.room_controls,text='Originalkarte importieren',command=self.import_original).pack(fill='x',pady=3)
        ttk.Label(self.room_controls,text='Raumeigenschaften').pack(anchor='w',pady=(12,3))
        for text,var in [('Name',self.name),('Breite in Pixeln',self.width),('Höhe in Pixeln',self.height)]:ttk.Label(self.room_controls,text=text).pack(anchor='w');ttk.Entry(self.room_controls,textvariable=var).pack(fill='x')
        ttk.Label(self.room_controls,text='Kollision / Spielebenen').pack(anchor='w');ttk.Combobox(self.room_controls,textvariable=self.collision_mode,state='readonly',values=('0 · Vordergrund','1 · Beide gemeinsam','2 · Vordergrund (nativ)','3 · Zwei Spielebenen'),width=24).pack(fill='x')
        ttk.Button(self.room_controls,text='Raumwerte übernehmen',command=self.apply_room).pack(fill='x',pady=4)
        if self.original_view:self.room_controls.pack_forget()
        self.canvas=tk.Canvas(center,bg='#171d27',highlightthickness=0)
        sx=ttk.Scrollbar(center,orient='horizontal',command=lambda *a:self.scroll('x',*a));sy=ttk.Scrollbar(center,command=lambda *a:self.scroll('y',*a))
        self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set);sy.pack(side='right',fill='y');sx.pack(side='bottom',fill='x');self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.schedule());self.canvas.bind('<Button-1>',self.press);self.canvas.bind('<B1-Motion>',self.motion);self.canvas.bind('<ButtonRelease-1>',self.release);self.canvas.bind('<Button-3>',self.pick)
        self.canvas.bind('<MouseWheel>',self.wheel);self.canvas.bind('<Button-2>',lambda e:self.canvas.scan_mark(e.x,e.y));self.canvas.bind('<B2-Motion>',self.pan)
        self.canvas.bind('<Motion>',self.hover_brush);self.canvas.bind('<Leave>',lambda e:self.hide_brush_cursor())
        self.canvas.bind('<Shift-Button-3>',self.pick_part)
        source_box=ttk.LabelFrame(right,text='Grafiken aus allen Abschnitten',padding=6);source_box.pack(fill='x',pady=(0,5))
        ttk.Label(source_box,text='Quelle').grid(row=0,column=0,sticky='w');self.source_picker=ttk.Combobox(source_box,textvariable=self.source_choice,values=tuple(f'{n} · {source_name(n)}' for n in range(SOURCE_COUNT)),width=18,state='readonly');self.source_picker.grid(row=0,column=1,sticky='ew');self.source_picker.bind('<<ComboboxSelected>>',self.source_changed)
        source_layer=ttk.Combobox(source_box,textvariable=self.source_layer,values=('front','back'),width=7,state='readonly');source_layer.grid(row=0,column=2,padx=4);source_layer.bind('<<ComboboxSelected>>',self.source_changed)
        ttk.Label(source_box,text='Quelle frei wählen, dann in jede Zielebene zeichnen.',wraplength=round(300*self.ui)).grid(row=1,column=0,columnspan=3,sticky='w')
        ttk.Button(source_box,text='Alle Grafikquellen vorbereiten',command=lambda:self.load_assets(range(SOURCE_COUNT))).grid(row=2,column=0,columnspan=3,sticky='ew',pady=(4,0))
        self.tabs=ttk.Notebook(right);self.tabs.pack(fill='both',expand=True)
        self.parts_tab=ttk.Frame(self.tabs);self.tabs.add(self.parts_tab,text='Bauteile')
        categories=ttk.Combobox(self.parts_tab,textvariable=self.part_category,values=CATEGORIES,state='readonly');categories.pack(fill='x',pady=3);categories.bind('<<ComboboxSelected>>',lambda e:self.refresh_parts())
        style.configure('Parts.Treeview',rowheight=round(86*self.ui))
        gallery=ttk.Frame(self.parts_tab);gallery.pack(fill='both',expand=True)
        self.parts_gallery=ttk.Treeview(gallery,show='tree',style='Parts.Treeview',height=3,selectmode='browse')
        part_scroll=ttk.Scrollbar(gallery,command=self.parts_gallery.yview);self.parts_gallery.configure(yscrollcommand=part_scroll.set);part_scroll.pack(side='right',fill='y');self.parts_gallery.pack(fill='both',expand=True)
        self.parts_gallery.bind('<<TreeviewSelect>>',self.choose_part)
        part_controls=ttk.Frame(self.parts_tab);part_controls.pack(side='bottom',fill='x')
        length=ttk.Frame(part_controls);length.pack(fill='x',pady=4)
        ttk.Label(length,text='Plattformlänge · Steine').pack(side='left')
        self.part_length_box=ttk.Spinbox(length,from_=1,to=32,textvariable=self.part_length,width=5,command=self.choose_part,state='disabled');self.part_length_box.pack(side='right');self.part_length_box.bind('<Return>',self.choose_part);self.part_length_box.bind('<FocusOut>',self.choose_part)
        self.brush_preview=tk.Canvas(part_controls,height=round(92*self.ui),bg='#202632',highlightthickness=0);self.brush_preview.pack(fill='x');self.brush_preview.bind('<Configure>',lambda e:self.refresh_brush())
        ttk.Label(part_controls,textvariable=self.brush_label,wraplength=round(300*self.ui)).pack(fill='x',pady=4)
        ttk.Label(part_controls,text='Ein Klick setzt das ganze Bauteil im 8px-Raster.',wraplength=round(300*self.ui)).pack(fill='x')
        ttk.Label(part_controls,text='Umschalt + Rechtsklick: vorhandene Plattform aufnehmen.',wraplength=round(300*self.ui)).pack(fill='x',pady=3)
        ttk.Entry(part_controls,textvariable=self.part_name).pack(fill='x',pady=(6,2))
        remember=ttk.Frame(part_controls);remember.pack(fill='x')
        ttk.Button(remember,text='Auswahl merken',command=self.remember_selection).pack(side='left',fill='x',expand=True)
        ttk.Button(remember,text='Pinsel merken',command=self.remember_brush).pack(side='left',fill='x',expand=True)
        ttk.Button(part_controls,text='Eigenes Bauteil entfernen',command=self.remove_part).pack(fill='x',pady=3)
        gallery.pack_forget();gallery.pack(fill='both',expand=True)
        self.block_canvas=self.palette_canvas('Blöcke 32px');self.tile_canvas=self.palette_canvas('Kacheln 8px')
        self.block_canvas.bind('<Button-1>',self.choose_block);self.tile_canvas.bind('<Button-1>',self.choose_tile)
        monsters=ttk.Frame(self.tabs);self.tabs.add(monsters,text='Monster')
        ttk.Entry(monsters,textvariable=self.filter).pack(fill='x');self.filter.trace_add('write',lambda *a:self.filter_monsters())
        style.configure('Sprites.Treeview',rowheight=round(66*self.ui))
        self.monsters=ttk.Treeview(monsters,show='tree',style='Sprites.Treeview');self.monsters.pack(fill='both',expand=True);self.monsters.bind('<<TreeviewSelect>>',lambda e:self.tool.set('Monster'))
        ttk.Label(monsters,text='Auswählen, dann in die Karte klicken. Mit „Auswahl“ ziehen; Werte / KI öffnet alle Einstellungen.',wraplength=290).pack(anchor='w',pady=5)
        objects=ttk.Frame(self.tabs);self.tabs.add(objects,text='Objekte')
        object_scroll=ttk.Scrollbar(objects);object_scroll.pack(side='right',fill='y')
        self.object_picker=ttk.Treeview(objects,show='tree',style='Sprites.Treeview',yscrollcommand=object_scroll.set);object_scroll.configure(command=self.object_picker.yview);self.object_picker.pack(fill='both',expand=True);self.object_picker.bind('<<TreeviewSelect>>',self.choose_object)
        ttk.Label(objects,text='O-0017: bewegliche Plattform, waagerecht oder senkrecht. Weitere Objekte laufen mit ihrer Originalfunktion.',wraplength=round(290*self.ui)).pack(fill='x',pady=5)
        props=ttk.LabelFrame(right,text='Auswahl / Ausgang',padding=7);self.object_props=props
        for n,(label,key) in enumerate([('X','x'),('Y','y'),('Variante','variant'),('Bewegung','motion'),('Zielraum','target'),('Ziel X','target_x'),('Ziel Y','target_y'),('Auslöser','trigger'),('Ebene / Zielebene','plane'),('Dein Name','name')]):
            ttk.Label(props,text=label).grid(row=n,column=0,sticky='w')
            if key in ('target','trigger','plane','motion'):
                control=ttk.Combobox(props,textvariable=self.props[key],width=20,state='readonly',values=('up','touch') if key=='trigger' else ('front','back') if key=='plane' else ('Waagerecht','Senkrecht') if key=='motion' else ())
                if key=='target':self.target_box=control
                if key=='motion':self.motion_box=control
            else:control=ttk.Entry(props,textvariable=self.props[key],width=16)
            if key=='variant':self.variant_entry=control
            control.grid(row=n,column=1,sticky='ew')
        ttk.Button(props,text='Übernehmen',command=self.apply_object).grid(row=10,column=0,sticky='ew',pady=5);ttk.Button(props,text='Löschen',command=self.delete).grid(row=10,column=1,sticky='ew')
        ttk.Label(props,textvariable=self.actor_stats,wraplength=round(290*self.ui)).grid(row=11,column=0,columnspan=2,sticky='w')
        ttk.Button(props,text='Werte / KI / Boss-Einstellungen …',command=self.actor_details).grid(row=12,column=0,columnspan=2,sticky='ew',pady=4)
        self.tabs.bind('<<NotebookTabChanged>>',self.part_tab_changed)
        ttk.Label(root,textvariable=self.status,padding=8,wraplength=1500).pack(fill='x')
        for key,fn in [('<Control-s>',self.save),('<Control-o>',self.open),('<Control-n>',self.new),('<Control-z>',self.undo),('<Control-y>',self.redo),('<F5>',self.test)]:root.bind(key,lambda e,f=fn:f())
        for key,fn in [('<Control-c>',self.copy),('<Control-v>',self.paste),('<Delete>',self.delete)]:self.canvas.bind(key,lambda e,f=fn:f())
        self.canvas.bind('<h>',lambda e:self.flip(True));self.canvas.bind('<v>',lambda e:self.flip(False));root.protocol('WM_DELETE_WINDOW',self.close)
        for key,delta in [('Left',(-1,0)),('Right',(1,0)),('Up',(0,-1)),('Down',(0,1))]:
            self.canvas.bind('<'+key+'>',lambda e,d=delta:self.nudge_actor(*d))
            self.canvas.bind('<Shift-'+key+'>',lambda e,d=delta:self.nudge_actor(d[0]*8,d[1]*8))
        raw=NativeSession.__new__(NativeSession);raw.bytes=(ROOT/'Super Castlevania IV (USA).sfc').read_bytes();catalog=raw.read_catalog()
        from level_bosses import profiles
        self.rom=raw.bytes;base_catalog=catalog+profiles(raw);self.catalog=base_catalog+scene_objects(raw,catalog);self.definitions=definitions(base_catalog,raw.bytes);self.object_types={e['type'] for e in self.catalog if e.get('category')=='object'};self.filter_monsters();self.filter_objects()
        self.refresh_rooms();self.load_assets([self.source_room.get(),1,2]);self.tick_id=root.after(60,self.tick)
        if self.original_view:self.originals.selection_set('0')

    def current(self):return self.original_room if self.original_view and self.original_room is not None else self.project.get(self.room_id)
    def editable(self):
        if self.original_view:
            self.status.set('Originalansicht · „Als eigene Kopie bearbeiten“ oder „Neues eigenes Level“ wählen.');return False
        return True
    def room_tab_changed(self,e=None):
        if str(self.room_tabs.select())==str(self.original_tab):
            self.room_controls.pack_forget()
            selected=self.originals.selection()
            if not selected:self.originals.selection_set('0')
            else:self.choose_original()
        else:
            self.room_controls.pack(side='bottom',fill='x',before=self.room_tabs)
            self.original_view=False;self.generation+=1;self.selected_object=None;self.selection=None;self.refresh_rooms()
    def choose_original(self,e=None):
        selection=self.originals.selection()
        if not selection or str(self.room_tabs.select())!=str(self.original_tab):return
        n=int(selection[0])
        if self.original_view and self.original_number==n and (self.original_loading or self.original_room is not None):return
        self.original_view=True;self.original_number=n;self.original_room=None;self.original_error='';self.original_loading=True;self.selected_object=None;self.selection=None;self.generation+=1;generation=self.generation
        self.copy_original_button.configure(state='disabled')
        self.canvas.xview_moveto(0);self.canvas.yview_moveto(0)
        self.status.set(f'Original R-{n:02d} wird vorbereitet …');self.schedule()
        def load():
            try:
                if n in self.original_cache:return 'original',dict(number=n,room=self.original_cache[n],error='',generation=generation)
                asset=Assets(ensure_room(n));r=asset.import_room(include_objects=True)
                return 'original',dict(number=n,room=r,error='',generation=generation)
            except Exception as exc:return 'original',dict(number=n,room=None,error=str(exc),generation=generation)
        self.background(load)
    def edit_original(self):
        if not self.original_view or self.original_room is None or self.original_loading:return False
        if not self.confirm():return False
        r=copy.deepcopy(self.original_room);r['id']='R-'+uuid.uuid4().hex[:8].upper();r['name']=f'Meine Kopie · R-{self.original_number:02d}'
        try:project=Project(dict(version=2,rom_sha256=self.project.data['rom_sha256'],name=r['name'],start_room=r['id'],rooms=[r]))
        except ValueError as exc:messagebox.showerror('Originalkopie',str(exc),parent=self.root);return False
        self.project=project;self.project.dirty=True;self.room_id=r['id'];self.original_view=False;self.generation+=1
        self.room_tabs.select(self.project_tab);self.refresh_rooms();self.status.set('Eigene Kopie · Änderungen werden nur in deinem Projekt gespeichert.');return True
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
                    self.refresh_parts();self.refresh_brush()
                    if value[2]:self.status.set(' · '.join(f'{source_name(n)}: {error}' for n,error in value[2]))
                elif value[0]=='sources_done' and not self.loading_assets and not self.failed_assets:
                    self.status.set('Grafikquellen bereit · Quelle und Zielebene frei kombinieren · F5 testen'+(' · '+self.current()['source_note'] if self.current().get('source_note') else ''))
                elif value[0]=='import':
                    if value[2]!=self.generation:continue
                    self.project.begin('Originalkarte importieren');r=value[1];self.project.data['rooms'].append(r);self.project.commit();self.room_id=r['id'];self.refresh_rooms();self.load_asset(r['tileset'])
                elif value[0]=='original':
                    result=value[1]
                    if result['generation']!=self.generation or not self.original_view:continue
                    self.original_loading=False;self.original_room=result['room'];self.original_error=result['error']
                    if self.original_room is not None:
                        self.copy_original_button.configure(state='normal')
                        self.original_cache[result['number']]=self.original_room;self.update_room();self.load_assets(sources(self.original_room))
                        self.status.set(f'Original R-{result["number"]:02d} · Vorschau · F5 spielt das Original · Zum Umbauen „Als eigene Kopie bearbeiten“.')
                    else:self.status.set(f'R-{result["number"]:02d}: {self.original_error} · F5 startet den Originalabschnitt; Grafikquellen bleiben verfügbar.')
                    self.schedule()
                elif value[0]=='play':
                    self.sprites.cache.clear();self.filter_monsters();self.filter_objects();self.schedule()
                    self.play_pending=False;self.playtest=value[1];self.playtest.session.lua.command('resume');self.status.set('Spieltest läuft in einem separaten Fenster'+(' ohne Ton (kein Audiogerät)' if self.playtest.audio_unavailable else '')+'. Mit „Test beenden“ schließen.')
        except queue.Empty:pass
        self.tick_id=self.root.after(60,self.tick)
    def refresh_rooms(self):
        self.rooms.delete(*self.rooms.get_children())
        if not any(r['id']==self.room_id for r in self.project.data['rooms']):self.room_id=self.project.data['rooms'][0]['id']
        for r in self.project.data['rooms']:self.rooms.insert('','end',iid=r['id'],text=('★ ' if r['id']==self.project.data['start_room'] else '')+r['name'])
        self.target_box.configure(values=tuple(r['id']+' · '+r['name'] for r in self.project.data['rooms']))
        self.rooms.selection_set(self.room_id);self.update_room();self.load_assets(sources(self.current()));self.schedule()
        self.refresh_parts()
    def choose_room(self,e=None):
        if str(self.room_tabs.select())!=str(self.project_tab):return
        if self.rooms.selection():self.room_id=self.rooms.selection()[0];self.selected_object=None;self.selection=None;self.update_room();self.load_assets(sources(self.current()));self.schedule()
    def update_room(self):
        r=self.current();self.name.set(r['name']);self.width.set(r['width']*8);self.height.set(r['height']*8);self.collision_mode.set(('0 · Vordergrund','1 · Beide gemeinsam','2 · Vordergrund (nativ)','3 · Zwei Spielebenen')[r.get('collision_mode',0)])
    def add_room(self,duplicate=False):
        if not self.editable():return
        source=self.current();r=self.project.add_room(source if duplicate else None,tileset=source['tileset'])
        self.room_id=r['id'];self.refresh_rooms();self.load_asset(r['tileset'])
    def set_start(self):
        if not self.editable():return
        self.project.begin('Startraum');self.project.data['start_room']=self.room_id;self.project.commit();self.refresh_rooms()
    def apply_room(self):
        if not self.editable():return
        try:
            width,height=self.width.get(),self.height.get()
            if width%8 or height%8:raise ValueError('Breite und Höhe müssen durch 8 teilbar sein.')
            r=self.current();self.project.resize(r,width//8,height//8,name=self.name.get().strip() or r['id'],collision_mode=int(self.collision_mode.get()[0]));self.refresh_rooms()
        except Exception as e:messagebox.showerror('Raum',str(e),parent=self.root)
    def import_original(self):
        if not self.editable():return
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
        if self.original_view and (self.original_loading or self.original_room is None):
            self.canvas.delete('all');text=f'Original R-{self.original_number:02d}\n'+('Wird vorbereitet …' if self.original_loading else self.original_error+'\n\nF5: Originalabschnitt spielen\nDie Grafikquellen stehen rechts zur Verfügung.')
            self.canvas.create_text(24,32,text=text,fill='#d5e1ed',anchor='nw',width=600,font=('Segoe UI',13));self.root.title(f'Castlevania IV · Original R-{self.original_number:02d}');return
        r=self.current();z=self.zoom.get();self.canvas.configure(scrollregion=(0,0,r['width']*8*z,r['height']*8*z))
        x0=max(0,int(self.canvas.canvasx(0)/z)//8);y0=max(0,int(self.canvas.canvasy(0)/z)//8)
        nx=min(r['width']-x0,int(self.canvas.winfo_width()/z/8)+2);ny=min(r['height']-y0,int(self.canvas.winfo_height()/z/8)+2)
        if nx<=0 or ny<=0:return
        image=self.room_image(r,x0,y0,nx,ny)
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
            x,y=a['x']*z,a['y']*z;selected=self.selected_object==('actor',a['id']);sprite=self.sprites.sprite(a)
            missing=sprite is None and (self.show_object_names.get() or any(d['type']==a['type'] for d in self.definitions))
            if selected or missing:
                bounds=self.actor_bounds(a);self.canvas.create_rectangle(*(v*z for v in bounds),outline='#f5db83' if selected else '#e8ae64',width=2)
            if selected or self.show_object_names.get() or missing:
                self.canvas.create_text(x,self.actor_bounds(a)[1]*z-4,text=self.actor_label(a),fill='#eff4ed',anchor='s',font=('Segoe UI',max(10,round(10*self.ui))))
            if selected and is_platform(a):self.canvas.create_line(*(v*z for v in platform_path(a)),fill='#75e4d6',dash=(5,3),arrow='last',width=2)
            if selected and a['type']>=128:
                entry=next((e for e in self.catalog if e['type']==a['type']),a);ox=entry.get('x',128)-a['x'];oy=entry.get('y',96)-a['y']
                left=max(-ox,max(0,min(r['width']*8-256,a['x']-128)));top=max(-oy,max(0,min(r['height']*8-224,a['y']-96)))
                self.canvas.create_rectangle(left*z,top*z,(left+256)*z,(top+224)*z,outline='#c5a0fc',dash=(6,4),width=2)
                self.canvas.create_text(left*z,top*z,text='Boss-Begegnung',fill='#d5baff',anchor='nw')
        for d in r['doors']:
            self.canvas.create_rectangle(d['x']*z,d['y']*z,(d['x']+d['w'])*z,(d['y']+d['h'])*z,outline='#7ebeff',width=3)
            self.canvas.create_text(d['x']*z,d['y']*z,text='→ '+d['target'],anchor='sw',fill='#9bd0ff')
        x,y=r['spawn'];self.canvas.create_oval((x-6)*z,(y-6)*z,(x+6)*z,(y+6)*z,fill='#63cde5',outline='white');self.canvas.create_text(x*z,(y-10)*z,text='START',fill='#9eeaff',anchor='s')
        if self.selection:
            x1,y1,x2,y2=self.selection;self.canvas.create_rectangle(x1*8*z,y1*8*z,(x2+1)*8*z,(y2+1)*8*z,outline='#f6e58d',dash=(5,3),width=2)
        self.show_brush_cursor()
        self.root.title(f'Castlevania IV · Original R-{self.original_number:02d} · Vorschau' if self.original_view else ('● ' if self.project.dirty else '')+'Castlevania IV · '+self.project.data['name'])
    def room_image(self,r,x0,y0,nx,ny):
        """Native-size map raster; sprites share the terrain's world coordinates."""
        image=Image.new('RGBA',(nx*8,ny*8),'#202632')
        for layer,shown in [('back',self.show_back.get()),('front',self.show_front.get())]:
            if shown:
                for yy in range(ny):
                    for xx in range(nx):image.alpha_composite(self.tile_image(r['layers'][layer][(y0+yy)*r['width']+x0+xx],r['tileset'],layer),(xx*8,yy*8))
            if shown:
                for actor in r['actors']:
                    if bool(actor.get('flags',0)&0x8000)!=(layer=='front'):continue
                    sprite=self.sprites.sprite(actor)
                    if sprite:
                        picture,anchor=sprite
                        px,py=actor['x']-anchor[0]-x0*8,actor['y']-anchor[1]-y0*8
                        if px<image.width and py<image.height and px+picture.width>0 and py+picture.height>0:image.alpha_composite(picture,(px,py))
        return image
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
        self.status.set(self.current().get('source_note') or 'Bereit · Linksklick zeichnen · Rechtsklick aufnehmen · Mitteltaste verschieben · Strg+Mausrad zoomen · H/V spiegeln · F5 testen');self.schedule();self.refresh_brush()
    def choose_block(self,e):
        asset=self.assets.get(self.source_room.get())
        if not asset:return
        x,y=self.block_canvas.canvasx(e.x)/self.ui,self.block_canvas.canvasy(e.y)/self.ui;n=int(y//32)*8+int(x//32)
        if not 0<=n<asset.block_count:return
        self.brush=[bind(w,self.source_room.get(),self.source_layer.get()) for w in asset.block(n,self.source_layer.get())];self.brush_width=4;self.brush_mask=None;self.recollision();self.tool.set('Zeichnen');self.refresh_brush();self.status.set(f'Quelle {source_name(self.source_room.get())} / {self.source_layer.get()} · Block {n:03X} · 32 × 32 Pixel')
    def choose_tile(self,e):
        asset=self.assets.get(self.source_room.get())
        if not asset:return
        x,y=self.tile_canvas.canvasx(e.x)/self.ui,self.tile_canvas.canvasy(e.y)/self.ui;n=int(y//20)*16+int(x//20)
        if not 0<=n<asset.tile_count:return
        self.brush=[bind(n|(self.palette.get()<<10),self.source_room.get(),self.source_layer.get())];self.brush_width=1;self.brush_mask=None;self.recollision();self.tool.set('Zeichnen');self.refresh_brush();self.status.set(f'Quelle {source_name(self.source_room.get())} / {self.source_layer.get()} · Kachel {n:03X} · 8 × 8 Pixel')
    def part_image(self,part):
        width=part['width'];image=Image.new('RGBA',(width*8,len(part['tiles'])//width*8))
        for i,value in enumerate(part['tiles']):
            if part['mask'][i]:image.alpha_composite(self.tile_image(value,0,'front'),(i%width*8,i//width*8))
        return image
    def part_tab_changed(self,e=None):
        if str(self.tabs.select())==str(self.parts_tab):self.object_props.pack_forget()
        else:self.object_props.pack(side='bottom',fill='x',pady=6,before=self.tabs)
    def refresh_parts(self):
        selected=self.parts_gallery.selection();self.parts={p['id']:p for p in builtin_parts(self.assets)+list(MOVING_PLATFORMS)+self.project.data.get('parts',[])}
        self.parts_gallery.delete(*self.parts_gallery.get_children());self.part_photos=[]
        category=self.part_category.get();custom={p['id'] for p in self.project.data.get('parts',[])}
        for key,part in self.parts.items():
            kind='Eigene' if key in custom else part['category']
            if category not in ('Alle',kind):continue
            size=(round(98*self.ui),round(70*self.ui))
            if part.get('kind')=='platform':image=self.sprites.thumbnail(part,size)
            else:image=self.part_image(part)
            scale=min(size[0]/image.width,size[1]/image.height,3*self.ui)
            preview=Image.new('RGBA',size,'#252c38');image=image.resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))),Image.Resampling.NEAREST)
            preview.alpha_composite(image,((size[0]-image.width)//2,(size[1]-image.height)//2));photo=ImageTk.PhotoImage(preview);self.part_photos.append(photo)
            if part.get('kind')=='platform':detail='32 × 16 px · 80 px pendeln'
            else:detail=f'{part["width"]*8} × {len(part["tiles"])//part["width"]*8} px'+(' · Länge wählbar' if part.get('repeatable') else '')
            self.parts_gallery.insert('','end',iid=key,text=part['name']+'\n'+detail,image=photo)
        if selected and self.parts_gallery.exists(selected[0]):self.parts_gallery.selection_set(selected[0])
    def choose_part(self,e=None):
        selection=self.parts_gallery.selection()
        if not selection or selection[0] not in self.parts:return
        base=self.parts[selection[0]];repeatable=base.get('repeatable',False)
        self.part_length_box.configure(state='normal' if repeatable else 'disabled')
        if base.get('kind')=='platform':self.select_object_template(base);return
        try:part=repeat_part(base,self.part_length.get() if repeatable else 1)
        except (ValueError,tk.TclError):self.status.set('Plattformlänge: 1 bis 32 Steine.');return
        self.brush=part['tiles'][:];self.brush_collision=part['collision'][:];self.brush_width=part['width'];self.brush_mask=part['mask'][:]
        self.tool.set('Bauteil');self.selected_object=None;self.refresh_brush()
        self.object_props.pack_forget()
        needed={resolve(v,0,'front')[0] for v in self.brush if v!=EMPTY}
        if needed-self.assets.keys():self.load_assets(needed)
        self.status.set(part['name']+' · Ein Klick setzt das ganze Bauteil · H/V spiegeln · Kollision wird mit übernommen, wenn eingeschaltet.')
    def pick_part(self,e):
        try:result=pick_connected_part(self.current(),self.layer.get(),*self.coords(e))
        except ValueError as exc:self.status.set(str(exc));return
        if result is None:self.status.set('Hier liegt auf der Zielebene keine feste Fläche. Für freie Ausschnitte „Auswahl“ verwenden.');return
        part,self.selection=result;self.brush=part['tiles'];self.brush_collision=part['collision'];self.brush_width=part['width'];self.brush_mask=part['mask']
        self.selected_object=None;self.tool.set('Bauteil');self.tabs.select(self.parts_tab);self.object_props.pack_forget();self.refresh_brush();self.schedule()
        self.status.set('Zusammenhängende Plattform aufgenommen. Linksklick setzt eine Kopie; „Pinsel merken“ speichert sie im Projekt.')
    def refresh_brush(self):
        if not hasattr(self,'brush_preview') or self.closing:return
        width=self.brush_preview.winfo_width();height=round(88*self.ui)
        if width<10:width=round(280*self.ui)
        if self.tool.get()=='Objekt' and self.object_template:
            image=self.sprites.thumbnail(self.object_template,(width,height))
            self.brush_photo=ImageTk.PhotoImage(image);self.brush_preview.delete('all');self.brush_preview.create_image(0,0,image=self.brush_photo,anchor='nw')
            self.brush_label.set(self.object_template['name']+(' · 80 Pixel Bewegung' if is_platform(self.object_template) else ''));self.show_brush_cursor();return
        part=dict(width=self.brush_width,tiles=self.brush,mask=self.brush_mask or [True]*len(self.brush));image=self.part_image(part)
        scale=min((width-12)/image.width,(height-12)/image.height,4*self.ui)
        image=image.resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))),Image.Resampling.NEAREST)
        self.brush_photo=ImageTk.PhotoImage(image);self.brush_preview.delete('all');self.brush_preview.create_image(width//2,height//2,image=self.brush_photo,anchor='center')
        self.brush_label.set(f'{self.brush_width*8} × {len(self.brush)//self.brush_width*8} Pixel · Zielebene: {self.layer.get()}')
        self.show_brush_cursor()
    def hide_brush_cursor(self):self.hover=None;self.canvas.delete('brush-cursor')
    def hover_brush(self,e):self.hover=self.coords(e);self.show_brush_cursor()
    def show_brush_cursor(self):
        self.canvas.delete('brush-cursor')
        if self.hover is None or self.tool.get() not in ('Bauteil','Objekt'):return
        x,y=self.hover;r=self.current()
        if not 0<=x<r['width'] or not 0<=y<r['height']:return
        z=self.zoom.get();w=self.brush_width;h=len(self.brush)//w
        if self.tool.get()=='Objekt' and self.object_template:
            actor=dict(self.object_template,x=x*8,y=y*8);bounds=self.actor_bounds(actor)
            self.canvas.create_rectangle(*(v*z for v in bounds),outline='#72e7d3',width=2,dash=(4,2),tags='brush-cursor')
            if is_platform(actor):self.canvas.create_line(*(v*z for v in platform_path(actor)),fill='#72e7d3',dash=(4,2),arrow='last',tags='brush-cursor')
            return
        self.canvas.create_rectangle(x*8*z,y*8*z,(x+w)*8*z,(y+h)*8*z,outline='#72e7d3',width=2,dash=(4,2),tags='brush-cursor')
    def add_part(self,part):
        if not self.editable():return
        validate_part(part)
        if len(self.project.data.get('parts',[]))>=128:raise ValueError('Höchstens 128 eigene Bauteile pro Projekt.')
        self.project.begin('Bauteil merken');self.project.data.setdefault('parts',[]).append(part);self.project.commit()
        self.part_category.set('Eigene');self.refresh_parts();self.parts_gallery.selection_set(part['id']);self.tabs.select(self.parts_tab)
        self.status.set('Bauteil gemerkt. Mit dem Projekt speichern; später per Klick wieder auswählen.');self.schedule()
    def remember_selection(self):
        if self.tool.get()=='Objekt':self.status.set('Spielobjekte direkt in der Karte auswählen; „Merken“ gilt für feste Bauteile.');return
        if not self.selection:self.status.set('Mit „Auswahl“ erst ein Rechteck um die gewünschte Plattform ziehen.');return
        try:self.add_part(capture_part(self.current(),self.layer.get(),self.selection,self.part_name.get()))
        except ValueError as exc:messagebox.showerror('Bauteil',str(exc),parent=self.root)
    def remember_brush(self):
        if self.tool.get()=='Objekt':self.status.set('Spielobjekte direkt in der Karte auswählen; „Merken“ gilt für feste Bauteile.');return
        try:
            part=dict(id='P-'+uuid.uuid4().hex[:12],name=self.part_name.get().strip(),category='Eigene',width=self.brush_width,
                tiles=[bind(v,self.current()['tileset'],self.layer.get()) for v in self.brush],collision=self.brush_collision[:],mask=self.brush_mask[:] if self.brush_mask is not None else [v!=EMPTY for v in self.brush])
            self.add_part(part)
        except ValueError as exc:messagebox.showerror('Bauteil',str(exc),parent=self.root)
    def remove_part(self):
        if not self.editable():return
        selection=self.parts_gallery.selection()
        if not selection or not any(p['id']==selection[0] for p in self.project.data.get('parts',[])):
            self.status.set('Hier lassen sich nur eigene gemerkte Bauteile entfernen.');return
        self.project.begin('Bauteil entfernen');self.project.data['parts']=[p for p in self.project.data['parts'] if p['id']!=selection[0]];self.project.commit();self.refresh_parts();self.schedule()
    def recollision(self):self.brush_collision=[self.tile_collision(w,self.current()['tileset'],self.layer.get()) for w in self.brush]
    def filter_monsters(self):
        self.monsters.delete(*self.monsters.get_children());term=self.filter.get().casefold();self.monster_photos=[]
        for m in self.definitions:
            label=m['code']+(' · Boss' if m['boss'] else '')
            if term in label.casefold():
                photo=ImageTk.PhotoImage(self.sprites.thumbnail(m,(round(58*self.ui),round(58*self.ui))));self.monster_photos.append(photo)
                self.monsters.insert('','end',iid=m['code'],text=label,image=photo)
    def filter_objects(self):
        monster_types={m['type'] for m in self.definitions}
        rows={f'object-{e["type"]:02x}-{e["variant"]:02x}':dict(e,name=f'O-{e["type"]:04X} · V{e["variant"]}') for e in self.catalog if e['type'] not in monster_types and e['type']!=0x17}
        rows['candle']=dict(type=14,variant=0x18,kind='candle',name='O-000E · Kerze')
        rows.update({p['id']:p for p in MOVING_PLATFORMS});self.object_rows=rows;self.object_photos=[]
        self.object_picker.delete(*self.object_picker.get_children())
        for key,row in rows.items():
            photo=ImageTk.PhotoImage(self.sprites.thumbnail(row,(round(58*self.ui),round(58*self.ui))));self.object_photos.append(photo)
            self.object_picker.insert('','end',iid=key,text=row['name']+(' · Grafik noch nicht erfasst' if not self.sprites.sprite(row) else '')+(' · Szenenobjekt' if row.get('kind')=='event' else ''),image=photo)
    def choose_object(self,e=None):
        selection=self.object_picker.selection()
        if selection:self.select_object_template(self.object_rows[selection[0]])
    def select_object_template(self,row):
        self.object_template=copy.deepcopy(row);self.tool.set('Objekt');self.selected_object=None;self.object_props.pack_forget();self.refresh_brush()
        self.status.set(row['name']+' · Linksklick setzt ein Spielobjekt · F5 startet seine echte Bewegung.')
    def actor_code(self,actor):return ('M-' if any(d['type']==actor['type'] for d in self.definitions) else 'O-')+f'{actor["type"]:04X}'
    def actor_label(self,actor):return self.actor_code(actor)+(' · '+actor['name'] if actor.get('name') else '')
    def actor_bounds(self,actor):
        sprite=self.sprites.sprite(actor)
        if sprite:
            image,anchor=sprite;box=image.getbbox()
            return (actor['x']-anchor[0]+box[0],actor['y']-anchor[1]+box[1],actor['x']-anchor[0]+box[2],actor['y']-anchor[1]+box[3])
        return (actor['x']-12,actor['y']-16,actor['x']+12,actor['y']+16)
    def coords(self,e):return int(self.canvas.canvasx(e.x)/(8*self.zoom.get())),int(self.canvas.canvasy(e.y)/(8*self.zoom.get()))
    def press(self,e):
        self.canvas.focus_set()
        if self.original_view and (self.original_loading or self.original_room is None):return
        if self.original_view and self.tool.get()!='Auswahl':self.editable();return
        r=self.current();x,y=self.coords(e)
        if not 0<=x<r['width'] or not 0<=y<r['height']:return
        self.start=(x,y);self.drag=(x,y)
        if not self.original_view:self.project.begin(self.tool.get())
        tool=self.tool.get()
        if tool!='Auswahl':self.selected_object=None
        if tool=='Auswahl':
            self.selected_object=None
            for kind,rows in [('actor',r['actors']),('door',r['doors'])]:
                for item in reversed(rows):
                    bounds=self.actor_bounds(item) if kind=='actor' else (item['x'],item['y'],item['x']+item['w'],item['y']+item['h'])
                    if bounds[0]<=x*8<bounds[2] and bounds[1]<=y*8<bounds[3]:self.selected_object=(kind,item['id']);break
                if self.selected_object:break
            if self.selected_object:
                item=self.object();self.object_drag_offset=(item['x']-x*8,item['y']-y*8);self.object_fields()
            else:self.selection=(x,y,x,y)
        elif tool in ('Zeichnen','Bauteil','Kollision'):self.stamp(x,y)
        elif tool=='Fläche':self.selection=(x,y,x,y)
        elif tool=='Start':r['spawn']=[x*8,y*8]
        elif tool=='Monster':
            selected=self.monsters.selection()
            if selected:
                t=int(selected[0][2:],16);entry=next(e for e in self.catalog if e['type']==t)
                item=dict(id='E-'+uuid.uuid4().hex[:8],type=t,variant=entry['variant'],x=x*8,y=y*8,flags=(entry['flags']&0x7fff)|(0x8000 if self.layer.get()=='front' else 0))
                if entry.get('boss'):item.update(kind='boss',boss_start='direct',boss_end='continue')
                r['actors'].append(item);self.selected_object=('actor',item['id']);self.object_fields()
        elif tool=='Objekt' and self.object_template:
            entry=self.object_template;item=dict(id='O-'+uuid.uuid4().hex[:8],type=entry['type'],variant=entry.get('variant',0),x=x*8,y=y*8,flags=0x8000 if self.layer.get()=='front' else 0)
            for key in ('kind','boss_start','boss_end','stats','native_family'):
                if key in entry:item[key]=copy.deepcopy(entry[key])
            if entry.get('_instance'):item['name']=entry.get('name','')
            if entry.get('kind')=='candle':item['kind']='candle'
            if is_platform(item):item['kind']='platform'
            try:validate_platform(item,r['width']*8,r['height']*8)
            except ValueError as exc:self.status.set(str(exc));return
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
            w=self.brush_width
            if self.tool.get()!='Bauteil':x=x//w*w;y=y//max(1,len(self.brush)//w)*max(1,len(self.brush)//w)
            paint(r,layer,x,y,self.brush,self.brush_collision if self.auto_collision.get() else None,w,mask=self.brush_mask)
    def motion(self,e):
        if self.start is None:return
        x,y=self.coords(e);self.hover=(x,y);r=self.current();tool=self.tool.get()
        if tool in ('Zeichnen','Kollision'):
            ox,oy=self.drag;n=max(abs(x-ox),abs(y-oy),1)
            for i in range(n+1):self.stamp(round(ox+(x-ox)*i/n),round(oy+(y-oy)*i/n))
        elif tool in ('Fläche','Auswahl') and not self.selected_object:self.selection=(max(0,min(self.start[0],x)),max(0,min(self.start[1],y)),min(r['width']-1,max(self.start[0],x)),min(r['height']-1,max(self.start[1],y)))
        elif tool=='Auswahl' and self.selected_object:
            if self.original_view:return
            item=self.object();ox,oy=getattr(self,'object_drag_offset',(0,0));xx,yy=max(0,min(r['width']*8-1,x*8+ox)),max(0,min(r['height']*8-1,y*8+oy))
            if item.get('kind')=='platform':
                xx=max(96 if item.get('variant',0)==0 else 16,min(r['width']*8-16,xx));yy=max(88 if item.get('variant',0)==1 else 8,min(r['height']*8-8,yy))
            item['x'],item['y']=xx,yy;self.object_fields()
        self.drag=(x,y);self.schedule()
    def release(self,e):
        if self.start is None:return
        if self.original_view:self.start=None;self.schedule();return
        if self.tool.get()=='Fläche' and self.selection:
            x1,y1,x2,y2=self.selection;w=self.brush_width;h=max(1,len(self.brush)//w)
            for y in range(y1,y2+1,h):
                for x in range(x1,x2+1,w):paint(self.current(),self.layer.get(),x,y,self.brush,self.brush_collision if self.auto_collision.get() else None,w,mask=self.brush_mask)
        self.project.commit();self.start=None;self.schedule()
    def pick(self,e):
        x,y=self.coords(e);r=self.current()
        if 0<=x<r['width'] and 0<=y<r['height']:
            self.brush=[bind(r['layers'][self.layer.get()][y*r['width']+x],r['tileset'],self.layer.get())];self.brush_collision=[r['collision'][self.layer.get()][y*r['width']+x]];self.brush_width=1;self.brush_mask=None;self.tool.set('Zeichnen');self.refresh_brush();self.status.set(f'Kachel mit Originalquelle aufgenommen: {self.brush[0]:08X}')
    def object(self):
        if not self.selected_object:return None
        kind,identifier=self.selected_object;return next((a for a in self.current()['actors' if kind=='actor' else 'doors'] if a['id']==identifier),None)
    def nudge_actor(self,dx,dy):
        if not self.editable():return
        item=self.object()
        if not item or self.selected_object[0]!='actor':return
        r=self.current();candidate=dict(item,x=max(0,min(r['width']*8-1,item['x']+dx)),y=max(0,min(r['height']*8-1,item['y']+dy)))
        try:validate_platform(candidate,r['width']*8,r['height']*8)
        except ValueError as exc:self.status.set(str(exc));return
        self.project.begin('Objekt verschieben');item.update(candidate);self.project.commit();self.object_fields();self.schedule()
        return 'break'
    def object_fields(self):
        item=self.object()
        if item:
            self.object_props.pack(side='bottom',fill='x',pady=6,before=self.tabs)
            for k,v in self.props.items():v.set(str(item.get(k,'')))
            moving=self.selected_object[0]=='actor' and is_platform(item)
            self.motion_box.configure(state='readonly' if moving else 'disabled');self.variant_entry.configure(state='readonly' if moving else 'normal')
            self.props['motion'].set(('Waagerecht' if item.get('variant',0)==0 else 'Senkrecht') if moving else '')
            self.props['plane'].set(('back' if item.get('flags',0)&0x8000==0 else 'front') if self.selected_object[0]=='actor' else ('back' if item.get('target_plane',0) else 'front'))
            if self.selected_object[0]=='actor':
                val=values_for(self.rom,item,self.current()['tileset']);self.actor_stats.set(f'HP: {val["hp"] if val["hp"] is not None else "Bossinitialisierung"} · Kontaktschaden: {val["contact_damage"]} · Trefferbereich: {val["half_width"]*2} × {val["half_height"]*2}')
            else:self.actor_stats.set('')
            if 'target' in item:
                target=self.project.get(item['target']);self.props['target'].set(target['id']+' · '+target['name'])
    def actor_details(self):
        item=self.object()
        if not item or self.selected_object[0]!='actor':return
        if self.stats_window and self.stats_window.winfo_exists():self.stats_window.destroy()
        window=tk.Toplevel(self.root);self.stats_window=window;window.title(self.actor_label(item)+' · Werte / KI');window.transient(self.root)
        box=ttk.Frame(window,padding=16);box.pack(fill='both',expand=True)
        ttk.Label(box,text=self.actor_label(item),font=('Segoe UI',16,'bold')).pack(anchor='w')
        table=ttk.Treeview(box,columns=('label','normal','ng','own'),show='headings',height=4)
        for key,label in [('label','Wert'),('normal','Normal'),('ng','New Game+'),('own','Wirksam (Normal)')]:table.heading(key,text=label);table.column(key,width=round(145*self.ui))
        table.pack(fill='x',pady=8);self.stats_table=table
        form=ttk.Frame(box);form.pack(fill='x');self.stat_fields={}
        for n,(key,label) in enumerate([('hp','Gesundheit'),('contact_damage','Kontaktschaden'),('half_width','Trefferbereich: halbe Breite'),('half_height','Trefferbereich: halbe Höhe')]):
            v=tk.StringVar(value=str(item.get('stats',{}).get(key,'')));self.stat_fields[key]=v
            ttk.Label(form,text=label).grid(row=n,column=0,sticky='w',padx=(0,12));ttk.Entry(form,textvariable=v,width=16,state='readonly' if self.original_view else 'normal').grid(row=n,column=1,sticky='ew')
        ttk.Label(box,text='Leeres Feld = Originalwert einschließlich Raum-/New-Game+-Bonus.\nEigene Werte ersetzen den Startwert dieses Exemplars im F5-Spieltest.',wraplength=round(610*self.ui)).pack(anchor='w',pady=8)
        self.boss_start=tk.StringVar(value=item.get('boss_start','direct'));self.boss_end=tk.StringVar(value=item.get('boss_end','continue'))
        if item['type']>=128:
            for label,var,choices in [('Bossstart',self.boss_start,('direct','sequence')),('Nach dem Sieg',self.boss_end,('continue','exit'))]:
                row=ttk.Frame(box);row.pack(fill='x');ttk.Label(row,text=label).pack(side='left');ttk.Combobox(row,textvariable=var,values=choices,state='readonly',width=18).pack(side='right')
            ttk.Label(box,text='direct: vorbereiteter Kampf · sequence: native Einleitung\ncontinue: Raum weiter erkunden · exit: erster Raumausgang nach dem Sieg\nEin Bosskampf ist eine einzelne Begegnung mit fester Kamera. Andere Gegner pausieren währenddessen.',wraplength=round(610*self.ui)).pack(anchor='w',pady=6)
        entry=next((e for e in self.catalog if e['type']==item['type']),item)
        notes='Kerzen verwenden die native Objekt-KI; Variante steuert den Inhalt (Original-Byte, dezimal).' if item['type']==14 else 'Originales Szenenobjekt: Variante und Position sind bearbeitbar. Solche Controller können Kamera, Kulisse oder Levelablauf steuern; ihre freie Kombination ist noch nicht vollständig geprüft.' if item.get('kind')=='event' else ai_notes(entry)
        if item['type']>=128:notes='Die originale Boss-KI läuft in einer einzelnen Begegnung gegen den spielbaren Simon. Körper, Geschosse und Hilfsteile bleiben zusammen. Native Angriffsphasen und feste Bewegungsgrenzen gelten weiterhin. Eigene Werte ändern den Startwert; eine neue KI oder vollständige Original-Levelsequenz entsteht dadurch nicht automatisch.'
        notes=notes.replace('„Natürlich“ zeigt den echten Ablauf.','F5 zeigt den echten Ablauf im eigenen Raum.')
        ttk.Label(box,text=notes,wraplength=round(610*self.ui),justify='left').pack(fill='x',pady=10)
        bar=ttk.Frame(box);bar.pack(fill='x');ttk.Button(bar,text='Werte übernehmen',state='disabled' if self.original_view else 'normal',command=lambda:self.apply_actor_stats(item['id'])).pack(side='left')
        ttk.Button(bar,text='Originalwerte wiederherstellen',state='disabled' if self.original_view else 'normal',command=lambda:self.reset_actor_stats(item['id'])).pack(side='left',padx=8)
        ttk.Button(bar,text='Schließen',command=window.destroy).pack(side='right');self.refresh_actor_stats(item)
    def refresh_actor_stats(self,item):
        self.stats_table.delete(*self.stats_table.get_children())
        n=values_for(self.rom,dict(item,stats={}),self.current()['tileset']);ng=values_for(self.rom,dict(item,stats={}),self.current()['tileset'],1);effective=values_for(self.rom,item,self.current()['tileset'])
        for key,label in [('hp','Gesundheit'),('contact_damage','Kontaktschaden'),('half_width','Halbe Trefferbreite'),('half_height','Halbe Trefferhöhe')]:
            self.stats_table.insert('','end',iid=key,values=(label,*('Initialisierung' if v[key] is None else v[key] for v in (n,ng,effective))))
    def apply_actor_stats(self,identifier):
        if not self.editable():return
        item=next((a for a in self.current()['actors'] if a['id']==identifier),None)
        if not item:return
        try:
            values={k:int(v.get()) for k,v in self.stat_fields.items() if v.get().strip()}
            candidate=dict(item,stats=values,boss_start=self.boss_start.get(),boss_end=self.boss_end.get())
            from level_actor_values import validate_values
            validate_values(candidate);self.project.begin('Monsterwerte');item.update(candidate);self.project.commit();self.refresh_actor_stats(item);self.object_fields();self.schedule()
        except ValueError as exc:messagebox.showerror('Monsterwerte',str(exc),parent=self.stats_window)
    def reset_actor_stats(self,identifier):
        for value in self.stat_fields.values():value.set('')
        self.apply_actor_stats(identifier)
    def apply_object(self):
        if not self.editable():return
        item=self.object()
        if not item:return
        try:
            values={k:int(self.props[k].get()) for k in ('x','y')}
            if self.selected_object[0]=='actor':
                values.update(name=self.props['name'].get().strip(),variant=int(self.props['variant'].get()),flags=(item.get('flags',0)&0x7fff)|(0x8000 if self.props['plane'].get()=='front' else 0))
                if is_platform(item):values.update(kind='platform',variant=0 if self.props['motion'].get()=='Waagerecht' else 1)
            else:values.update(target=self.props['target'].get().split(' · ')[0],target_x=int(self.props['target_x'].get()),target_y=int(self.props['target_y'].get()),trigger=self.props['trigger'].get(),target_plane=int(self.props['plane'].get()=='back'))
            self.project.begin('Objektwerte');item.update(values)
            from level_project import validate
            validate(self.project.data);self.project.commit();self.schedule()
        except Exception as e:
            if self.project.transaction:self.project.data=self.project.transaction[1];self.project.transaction=None
            messagebox.showerror('Objekt',str(e),parent=self.root)
    def delete(self):
        if not self.editable():return
        self.project.begin('Löschen');r=self.current()
        if self.selected_object:
            kind,identifier=self.selected_object;key='actors' if kind=='actor' else 'doors';r[key]=[a for a in r[key] if a['id']!=identifier];self.selected_object=None
        elif self.selection:
            x1,y1,x2,y2=self.selection
            for y in range(y1,y2+1):
                for x in range(x1,x2+1):paint(r,self.layer.get(),x,y,[EMPTY],[0])
        self.project.commit();self.schedule()
    def copy(self):
        if self.selected_object and self.selected_object[0]=='actor':
            self.actor_clipboard=dict(copy.deepcopy(self.object()),_instance=True);self.status.set(self.actor_label(self.actor_clipboard)+' kopiert · Strg+V, dann in die Karte klicken.');return
        if not self.selection:return
        self.actor_clipboard=None;r=self.current();x1,y1,x2,y2=self.selection;w=x2-x1+1
        self.clipboard=([bind(r['layers'][self.layer.get()][y*r['width']+x],r['tileset'],self.layer.get()) for y in range(y1,y2+1) for x in range(x1,x2+1)],
                        [r['collision'][self.layer.get()][y*r['width']+x] for y in range(y1,y2+1) for x in range(x1,x2+1)],w)
        self.status.set(f'Ausschnitt {w*8} × {(y2-y1+1)*8} Pixel kopiert.')
    def paste(self):
        if getattr(self,'actor_clipboard',None):
            self.select_object_template(dict(self.actor_clipboard,name=self.actor_clipboard.get('name') or self.actor_code(self.actor_clipboard)));return
        if self.clipboard:self.brush,self.brush_collision,self.brush_width=copy.deepcopy(self.clipboard);self.brush_mask=None;self.tool.set('Zeichnen');self.refresh_brush();self.status.set('Ausschnitt mit Linksklick platzieren.')
    def flip(self,horizontal):
        w=self.brush_width;h=len(self.brush)//w;indices=[(y*w+(w-1-x) if horizontal else (h-1-y)*w+x) for y in range(h) for x in range(w)]
        values=[];collisions=[]
        for i in indices:
            old=self.brush[i];value=old^(0x4000 if horizontal else 0x8000) if old!=EMPTY else EMPTY
            collision=self.brush_collision[i]
            if collision==self.tile_collision(old,self.current()['tileset'],self.layer.get()):collision=self.tile_collision(value,self.current()['tileset'],self.layer.get())
            values.append(value);collisions.append(collision)
        self.brush,self.brush_collision=values,collisions
        if self.brush_mask is not None:self.brush_mask=[self.brush_mask[i] for i in indices]
        self.refresh_brush()
    def undo(self):
        if self.editable():self.project.undo();self.selected_object=None;self.refresh_rooms()
    def redo(self):
        if self.editable():self.project.redo();self.selected_object=None;self.refresh_rooms()
    def confirm(self):return not self.project.dirty or messagebox.askyesno('Ungespeicherte Änderungen','Ohne Speichern fortfahren?',parent=self.root)
    def new(self):
        if self.confirm():self.original_view=False;self.generation+=1;self.project=Project();self.room_id=self.project.data['rooms'][0]['id'];self.room_tabs.select(self.project_tab);self.refresh_rooms();self.load_asset(0)
    def open(self):
        if not self.confirm():return
        name=filedialog.askopenfilename(parent=self.root,initialdir=self.project_directory(),filetypes=[('Castlevania-Level','*.sc4level.json'),('JSON','*.json')])
        if name:
            try:self.project=Project.load(name);self.original_view=False;self.generation+=1;self.room_id=self.project.data['start_room'];self.room_tabs.select(self.project_tab);self.refresh_rooms();self.load_asset(self.current()['tileset'])
            except Exception as e:messagebox.showerror('Öffnen',str(e),parent=self.root)
    def save(self,as_new=False):
        if self.original_view and not self.edit_original():return
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
        self.play_pending=True;scale=round(3*self.ui);self.status.set('Bossbegegnungen werden bei Bedarf einmalig vorbereitet; danach startet der Spieltest …' if not self.original_view and any(a['type']>=128 for r in data['rooms'] for a in r['actors']) else 'Spieltest wird vorbereitet …')
        if self.original_view:
            number=self.original_number;self.background(lambda:('play',OriginalPlaytest(number,folder,window_scale=scale)))
        else:self.background(lambda:('play',Playtest(data,folder,window_scale=scale)))
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
