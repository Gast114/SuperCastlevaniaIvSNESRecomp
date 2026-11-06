"""Visual Castlevania IV room editor with native playtests and separate projects."""
import argparse
import copy
import json
from pathlib import Path
import queue
import tempfile
import threading
import uuid
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from PIL import Image,ImageDraw,ImageTk
from level_project import Project,paint,room,MAX_ACTORS
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
        self.zoom=tk.DoubleVar(value=2);self.layer=tk.StringVar(value='front');self.tool=tk.StringVar(value='Auswahl')
        self.show_back=tk.BooleanVar(value=True);self.show_front=tk.BooleanVar(value=True);self.show_collision=tk.BooleanVar(value=False)
        self.show_object_names=tk.BooleanVar(value=True)
        self.actor_stats=tk.StringVar();self.stats_window=None;self.stat_fields={}
        self.auto_collision=tk.BooleanVar(value=True);self.grid=tk.BooleanVar(value=False);self.collision=tk.IntVar(value=1);self.palette=tk.IntVar(value=2)
        self.status=tk.StringVar(value='Grafiksatz wird vorbereitet …');self.origin_room=tk.IntVar(value=0);self.filter=tk.StringVar()
        self.source_room=tk.IntVar(value=self.current()['tileset']);self.source_layer=tk.StringVar(value='front')
        self.source_choice=tk.StringVar(value=f'{self.source_room.get()} · {source_name(self.source_room.get())}')
        self.name=tk.StringVar();self.width=tk.IntVar();self.height=tk.IntVar();self.collision_mode=tk.StringVar();self.props={k:tk.StringVar() for k in ('x','y','variant','target_x','target_y','target','trigger','plane','motion','name')}
        self.ui=max(1.,min(1.7,root.winfo_screenwidth()/1920));root.tk.call('tk','scaling',96/72*self.ui)
        self.monster_template=None;self.library_drag=None;self.preview_photos={};self.pixel_drag=None;self.placement_once=False
        root.title('Castlevania IV · Level-Editor');root.geometry(f'{min(round(1680*self.ui),root.winfo_screenwidth()-80)}x{min(round(1020*self.ui),root.winfo_screenheight()-100)}')
        root.minsize(min(round(1120*self.ui),root.winfo_screenwidth()-80),min(round(760*self.ui),root.winfo_screenheight()-100))
        from level_editor_ui import build
        build(self)
        raw=NativeSession.__new__(NativeSession);raw.bytes=(ROOT/'Super Castlevania IV (USA).sfc').read_bytes();catalog=raw.read_catalog()
        from level_bosses import profiles
        try:self.library_names=json.loads((ROOT.parent/'Assets (ausgeschnitten)/Gegner/Werkstatt/project.json').read_text(encoding='utf-8')).get('monster_names',{})
        except (OSError,ValueError):self.library_names={}
        self.rom=raw.bytes;base_catalog=catalog+profiles(raw);self.catalog=base_catalog+scene_objects(raw,catalog);self.definitions=definitions(base_catalog,raw.bytes);self.object_types={e['type'] for e in self.catalog if e.get('category')=='object'};self.filter_monsters();self.filter_objects()
        from level_studio import MonsterPanel
        self.studio=MonsterPanel(self);self.workspaces.bind('<<NotebookTabChanged>>',self.workspace_changed)
        self.refresh_rooms();self.load_assets([self.source_room.get(),1,2]);self.tick_id=root.after(60,self.tick)
        if self.original_view:self.originals.selection_set('0')

    def current(self):return self.original_room if self.original_view and self.original_room is not None else self.project.get(self.room_id)
    def open_monster_workshop(self,entry=None):
        self.studio.source(entry);self.workspaces.select(self.monster_page);self.studio.show();self.workspace_header()
    def workspace_changed(self,e=None):
        if str(self.workspaces.select())==str(self.monster_page):
            if not self.studio.visible:self.open_monster_workshop()
        else:self.studio.hide()
        self.workspace_header()
    def workspace_header(self):
        monster=self.studio.visible
        self.save_button.configure(text='Monster speichern' if monster else 'Speichern')
        self.test_button.configure(text='▶ Monster testen   F5' if monster else '▶ Spieltest   F5');self.stop_button.configure(text='⏸ Vorschau pausieren' if monster else '■ Test beenden')
        if monster:self.root.title('Castlevania Studio · Monster & Animationen')
    def editable(self):
        if self.original_view:
            self.status.set('Zum Bearbeiten oben „Bearbeiten“ wählen oder eine Figur ziehen.');return False
        return True
    def room_tab_changed(self,e=None):
        if str(self.room_tabs.select())==str(self.original_tab):
            self.room_controls.pack_forget()
            selected=self.originals.selection()
            if not selected:self.originals.selection_set('0')
            else:self.choose_original()
        else:
            self.room_controls.pack(side='bottom',fill='x',before=self.room_tabs)
            if not self.original_view:self.update_room();self.schedule();return
            self.original_view=False;self.generation+=1;self.selected_object=None;self.selection=None;self.refresh_rooms()
    def choose_original(self,e=None):
        selection=self.originals.selection()
        if not selection or str(self.room_tabs.select())!=str(self.original_tab):return
        n=int(selection[0])
        if self.original_view and self.original_number==n and (self.original_loading or self.original_room is not None):return
        self.original_view=True;self.original_number=n;self.original_room=None;self.original_error='';self.original_loading=True;self.selected_object=None;self.selection=None;self.generation+=1;generation=self.generation
        self.copy_original_button.configure(state='disabled')
        self.mode_title.set(f'Originalvorlage · R-{n:02d}');self.mode_hint.set('Abschnitt wird geladen …');self.edit_button.configure(state='disabled');self.edit_button.pack(side='right',padx=(12,0))
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
        r=copy.deepcopy(self.original_room);r['id']='R-'+uuid.uuid4().hex[:8].upper();r['name']=f'Meine Kopie · R-{self.original_number:02d}'
        occupied=self.project.path is not None or self.project.dirty or len(self.project.data['rooms'])>1 or any(q['actors'] or q['doors'] or any(v!=EMPTY for a in q['layers'].values() for v in a) for q in self.project.data['rooms'])
        try:
            if occupied:r=self.project.add_room(r);project=self.project
            else:project=Project(dict(version=2,rom_sha256=self.project.data['rom_sha256'],name=r['name'],start_room=r['id'],rooms=[r]))
        except ValueError as exc:messagebox.showerror('Originalkopie',str(exc),parent=self.root);return False
        self.project=project;self.project.dirty=True;self.room_id=r['id'];self.original_view=False;self.generation+=1
        self.room_tabs.select(self.project_tab);self.refresh_rooms();self.status.set('Eigene Kopie · Änderungen werden nur in deinem Projekt gespeichert.');return True
    def ensure_editable(self):
        if self.original_view and (self.original_loading or self.original_room is None):
            self.status.set('Der Abschnitt wird noch geladen …' if self.original_loading else 'Dieser Abschnitt hat noch keine bearbeitbare Kartenansicht. Links „Eigenes Level beginnen“ wählen oder einen anderen Abschnitt öffnen.');return False
        return self.edit_original() if self.original_view else True
    def room_dialog(self):
        if not self.ensure_editable():return
        self.update_room();window=tk.Toplevel(self.root);window.title('Raumeigenschaften');window.transient(self.root)
        box=ttk.Frame(window,padding=18);box.pack(fill='both',expand=True)
        for n,(title,value) in enumerate([('Name',self.name),('Breite in Pixeln',self.width),('Höhe in Pixeln',self.height)]):
            ttk.Label(box,text=title).grid(row=n,column=0,sticky='w',padx=(0,12),pady=5);ttk.Entry(box,textvariable=value,width=26).grid(row=n,column=1,sticky='ew')
        ttk.Label(box,text='Spielebenen / Kollision').grid(row=3,column=0,sticky='w')
        ttk.Combobox(box,textvariable=self.collision_mode,state='readonly',values=('0 · Vordergrund','1 · Beide gemeinsam','2 · Vordergrund (nativ)','3 · Zwei Spielebenen'),width=26).grid(row=3,column=1)
        ttk.Button(box,text='Übernehmen',style='Accent.TButton',command=self.apply_room).grid(row=4,column=0,columnspan=2,sticky='ew',pady=(12,0))
    def import_dialog(self):
        window=tk.Toplevel(self.root);window.title('Originalabschnitt hinzufügen');window.transient(self.root)
        box=ttk.Frame(window,padding=18);box.pack(fill='both',expand=True)
        ttk.Label(box,text='Originalabschnitt 0–67').pack(anchor='w');ttk.Spinbox(box,from_=0,to=67,textvariable=self.origin_room,width=20).pack(fill='x',pady=8)
        ttk.Button(box,text='Zum Projekt hinzufügen',style='Accent.TButton',command=lambda:(self.import_original(),window.destroy())).pack(fill='x')
    def open_palette(self,name):
        self.tabs.select({'Gegner':self.monster_tab,'Objekte':self.objects_tab,'Gelände':self.terrain_tab}[name])
        self.cancel_placement()
        if name=='Gegner':self.monster_search.focus_set()
        self.context_hint.set('Bild auswählen und „Hinzufügen“ drücken – oder ein Bild in die Karte ziehen.' if name!='Gelände' else 'Bauteil oder Kachel auswählen, dann in die Karte zeichnen.')
    def mode_changed(self):
        if not hasattr(self,'context_hint'):return
        mode=self.tool.get();placing=mode in ('Monster','Objekt')
        self.canvas.configure(cursor='crosshair' if mode!='Auswahl' else 'arrow')
        self.context_hint.set('In die Karte klicken zum Platzieren · Umschalt: mehrfach setzen · Esc: beenden' if placing else 'Figuren direkt anklicken und ziehen · Doppelklick: Werte / KI · Mittlere Maustaste: Karte verschieben' if mode=='Auswahl' else 'In die Karte klicken oder ziehen · Esc: zurück zum Auswählen')
        self.show_brush_cursor()
    def cancel_placement(self):
        self.library_drag=None;self.placement_once=False;self.tool.set('Auswahl');self.hide_brush_cursor()
    def library_entry(self,kind):
        if kind=='Monster':
            selected=self.monsters.selection()
            if selected:
                if self.monster_template and f'M-{self.monster_template["type"]:04X}'==selected[0]:return self.monster_template
                return next((e for e in self.catalog if f'M-{e["type"]:04X}'==selected[0]),None)
        else:
            selected=self.object_picker.selection()
            if selected:return self.object_rows.get(selected[0])
        return None
    def choose_monster(self,e=None):
        row=self.library_entry('Monster')
        if row:self.monster_template=row;self.library_preview('Monster',row)
    def library_preview(self,kind,row):
        title=(self.actor_label(row) if kind=='Monster' else row.get('name',self.actor_code(row)))
        self.library_titles[kind].set(title+'\nBereit zum Hinzufügen')
        canvas=self.library_previews[kind];size=(round(78*self.ui),round(70*self.ui))
        photo=ImageTk.PhotoImage(self.sprites.thumbnail(row,size));self.preview_photos[kind]=photo;canvas.delete('all');canvas.create_image(0,0,image=photo,anchor='nw')
        for button in self.library_actions[kind]:button.configure(state='normal')
    def arm_library(self,kind):
        row=self.library_entry(kind)
        if not row:return
        if kind=='Monster':self.monster_template=row
        else:self.object_template=copy.deepcopy(row)
        self.tool.set(kind);self.selected_object=None;self.object_props.pack_forget();self.placement_once=True;self.canvas.focus_set();self.status.set('In der Karte auf die gewünschte Stelle klicken. Esc beendet das Platzieren.')
    def add_from_library(self,kind):
        row=self.library_entry(kind)
        if not row:return
        canvas=self.canvas;z=self.zoom.get();width=canvas.winfo_width();height=canvas.winfo_height()
        r=self.current()
        x=round((max(0,canvas.canvasx(0)/z)+min(r['width']*8,canvas.canvasx(width)/z))/2) if width>10 else 160
        y=round((max(0,canvas.canvasy(0)/z)+min(r['height']*8,canvas.canvasy(height)/z))/2) if height>10 else 120
        self.place_actor(row,x,y);return 'break'
    def place_actor(self,row,x,y):
        if not self.ensure_editable():return
        r=self.current();x=max(0,min(r['width']*8-1,int(x)));y=max(0,min(r['height']*8-1,int(y)))
        if len(r['actors'])>=MAX_ACTORS:self.status.set(f'In diesem Raum sind bereits {MAX_ACTORS} Figuren. Bitte zuerst eine Figur entfernen.');return
        actor=dict(id='E-'+uuid.uuid4().hex[:8],type=row['type'],variant=row.get('variant',0),x=x,y=y,flags=(row.get('flags',0)&0x7fff)|(0x8000 if self.layer.get()=='front' else 0))
        for key in ('kind','boss_start','boss_end','stats','native_family'):
            if key in row:actor[key]=copy.deepcopy(row[key])
        if row.get('_instance'):actor['name']=row.get('name','')
        if row.get('boss') or actor['type']>=128:actor.setdefault('kind','boss');actor.setdefault('boss_start','direct');actor.setdefault('boss_end','continue')
        if is_platform(actor):
            actor['kind']='platform';actor['x']=max(96 if actor['variant']==0 else 16,min(r['width']*8-16,x));actor['y']=max(88 if actor['variant']==1 else 8,min(r['height']*8-8,y))
        validate_platform(actor,r['width']*8,r['height']*8)
        self.project.begin('Figur hinzufügen');r['actors'].append(actor);self.project.commit();self.selected_object=('actor',actor['id']);self.selection=None;self.tool.set('Auswahl');self.object_fields();self.schedule()
        self.status.set(self.actor_label(actor)+' hinzugefügt · Direkt mit der Maus ziehen oder links die Werte ändern.');return actor
    def duplicate_actor(self):
        actor=self.object()
        if actor and self.selected_object[0]=='actor':self.place_actor(dict(copy.deepcopy(actor),_instance=True),actor['x']+16,actor['y']+8)
    def library_press(self,e,kind):
        identifier=e.widget.identify_row(e.y)
        if not identifier:return
        e.widget.selection_set(identifier);self.library_drag=dict(kind=kind,start=(e.x_root,e.y_root),moving=False)
    def library_motion(self,e):
        if not self.library_drag:return
        if abs(e.x_root-self.library_drag['start'][0])+abs(e.y_root-self.library_drag['start'][1])<6:return
        self.library_drag['moving']=True;canvas=self.canvas;x=e.x_root-canvas.winfo_rootx();y=e.y_root-canvas.winfo_rooty()
        row=self.library_entry(self.library_drag['kind']);canvas.delete('library-drop')
        if row and 0<=x<canvas.winfo_width() and 0<=y<canvas.winfo_height():
            wx,wy=self.pixel_coords(SimpleNamespace(x=x,y=y));bounds=self.actor_bounds(dict(row,x=wx,y=wy));z=self.zoom.get()
            canvas.create_rectangle(*(v*z for v in bounds),outline='#8da6ff',width=2,dash=(5,3),tags='library-drop')
        return 'break'
    def library_release(self,e):
        drag=self.library_drag;self.library_drag=None;self.canvas.delete('library-drop')
        if not drag or not drag['moving']:return
        row=self.library_entry(drag['kind']);x=e.x_root-self.canvas.winfo_rootx();y=e.y_root-self.canvas.winfo_rooty()
        if row and 0<=x<self.canvas.winfo_width() and 0<=y<self.canvas.winfo_height():self.place_actor(row,*self.pixel_coords(SimpleNamespace(x=x,y=y)))
        return 'break'
    def inspect_at(self,e):
        hit=self.hit_object(*self.pixel_coords(e))
        if hit:self.selected_object=hit;self.object_fields();self.actor_details();return 'break'
    def palette_canvas(self,title):
        f=ttk.Frame(self.terrain_tabs);self.terrain_tabs.add(f,text=title);c=tk.Canvas(f,bg='#252c38',width=290,height=350,highlightthickness=0)
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
                        self.edit_button.configure(state='normal')
                        self.original_cache[result['number']]=self.original_room;self.update_room();self.load_assets(sources(self.original_room))
                        self.status.set(f'Original R-{result["number"]:02d} · Vorschau · F5 spielt das Original · Zum Umbauen „Als eigene Kopie bearbeiten“.')
                    else:
                        self.mode_hint.set('Kartenansicht noch nicht verfügbar. F5 spielt diesen Originalabschnitt.');self.status.set(f'R-{result["number"]:02d}: {self.original_error} · F5 startet den Originalabschnitt; Grafikquellen bleiben verfügbar.')
                    self.schedule()
                elif value[0]=='play':
                    if self.studio.visible:self.play_pending=False;value[1].close();continue
                    self.sprites.cache.clear();self.filter_monsters();self.filter_objects();self.schedule()
                    self.play_pending=False;self.playtest=value[1];self.playtest.show();self.playtest.session.lua.command('resume');self.status.set('Spieltest läuft in einem separaten Fenster'+(' ohne Ton (kein Audiogerät)' if self.playtest.audio_unavailable else '')+'. Mit „Test beenden“ schließen.')
                    if getattr(self.playtest,'notes',''):self.status.set(self.status.get()+' '+self.playtest.notes)
                elif value[0]=='studio_workspace':self.studio.ready(value[1])
                elif value[0]=='studio_error':self.studio.failed(value[1])
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
        if self.rooms.selection() and self.rooms.selection()[0]==self.room_id:return
        if self.rooms.selection():self.room_id=self.rooms.selection()[0];self.selected_object=None;self.selection=None;self.update_room();self.load_assets(sources(self.current()));self.schedule()
    def update_room(self):
        r=self.current();self.name.set(r['name']);self.width.set(r['width']*8);self.height.set(r['height']*8);self.collision_mode.set(('0 · Vordergrund','1 · Beide gemeinsam','2 · Vordergrund (nativ)','3 · Zwei Spielebenen')[r.get('collision_mode',0)])
        self.mode_title.set(f'Originalvorlage · R-{self.original_number:02d}' if self.original_view else r['name'])
        self.mode_hint.set('Eine Figur ziehen oder hinzufügen erstellt automatisch eine eigene Kopie.' if self.original_view else 'Bearbeitbar · Figuren direkt ziehen · Änderungen mit Speichern sichern')
        if self.original_view:self.edit_button.pack(side='right',padx=(12,0))
        else:self.edit_button.pack_forget()
        if not self.object():self.object_props.pack_forget()
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
        self.status.set(f'Originalkarte R-{n:02d} wird eingelesen …');self.background(lambda:('import',Assets(ensure_room(n)).import_room(include_objects=True),generation))
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
        if hasattr(self,'studio') and self.studio.visible:return
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
            ax,ay=self.actor_position(a);x,y=ax*z,ay*z;selected=self.selected_object==('actor',a['id']);sprite=self.sprites.sprite(a)
            missing=sprite is None and (self.show_object_names.get() or any(d['type']==a['type'] for d in self.definitions))
            if selected or missing:
                bounds=self.actor_bounds(a);self.canvas.create_rectangle(*(v*z for v in bounds),outline='#f5db83' if selected else '#e8ae64',width=2)
            if selected or self.show_object_names.get() or missing:
                self.canvas.create_text(x,self.actor_bounds(a)[1]*z-4,text=self.actor_label(a),fill='#eff4ed',anchor='s',font=('Segoe UI',max(10,round(10*self.ui))),tags=('actor-label-'+a['id'],))
            if selected and is_platform(a):self.canvas.create_line(*(v*z for v in platform_path(a)),fill='#75e4d6',dash=(5,3),arrow='last',width=2)
            if selected and a['type']>=128:
                from level_bosses import arena_floor
                entry=next((e for e in self.catalog if e['type']==a['type']),a);ox=entry.get('x',128)-a['x'];oy=192-arena_floor(r,a)
                left=max(-ox,max(0,min(r['width']*8-256,a['x']-128)));top=max(-oy,max(0,min(r['height']*8-224,-oy)))
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
                        ax,ay=self.actor_position(actor);px,py=ax-anchor[0]-x0*8,ay-anchor[1]-y0*8
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
        if self.object():self.object_fields()
        else:self.object_props.pack_forget()
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
        self.selected_object=None;self.tool.set('Bauteil');self.tabs.select(self.terrain_tab);self.terrain_tabs.select(self.parts_tab);self.object_props.pack_forget();self.refresh_brush();self.schedule()
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
    def hide_brush_cursor(self):self.hover=None;self.hover_pixel=None;self.canvas.delete('brush-cursor')
    def hover_brush(self,e):
        self.hover=self.coords(e);self.hover_pixel=self.pixel_coords(e)
        if self.tool.get()=='Auswahl' and not self.original_loading:self.canvas.configure(cursor='hand2' if self.hit_object(*self.hover_pixel) else 'arrow')
        self.show_brush_cursor()
    def show_brush_cursor(self):
        self.canvas.delete('brush-cursor')
        if self.hover is None or self.tool.get() not in ('Bauteil','Objekt','Monster'):return
        x,y=self.hover;r=self.current()
        if not 0<=x<r['width'] or not 0<=y<r['height']:return
        z=self.zoom.get();w=self.brush_width;h=len(self.brush)//w
        row=self.library_entry('Monster') or self.monster_template if self.tool.get()=='Monster' else self.object_template if self.tool.get()=='Objekt' else None
        if self.tool.get() in ('Monster','Objekt') and row is None:return
        if row:
            px,py=getattr(self,'hover_pixel',None) or (x*8,y*8);actor=dict(row,x=px,y=py);bounds=self.actor_bounds(actor);sprite=self.sprites.sprite(actor)
            if sprite:
                picture,anchor=sprite;key=(actor['type'],actor.get('variant',0),z,id(picture))
                if key!=getattr(self,'cursor_key',None):
                    ghost=picture.copy();ghost.putalpha(ghost.getchannel('A').point(lambda a:a*3//5));ghost=ghost.resize((max(1,round(ghost.width*z)),max(1,round(ghost.height*z))),Image.Resampling.NEAREST)
                    self.cursor_photo=ImageTk.PhotoImage(ghost);self.cursor_key=key
                ax,ay=self.actor_position(actor);self.canvas.create_image((ax-anchor[0])*z,(ay-anchor[1])*z,image=self.cursor_photo,anchor='nw',tags='brush-cursor')
            self.canvas.create_rectangle(*(v*z for v in bounds),outline='#72e7d3',width=2,dash=(4,2),tags='brush-cursor')
            if is_platform(actor):self.canvas.create_line(*(v*z for v in platform_path(actor)),fill='#72e7d3',dash=(4,2),arrow='last',tags='brush-cursor')
            return
        self.canvas.create_rectangle(x*8*z,y*8*z,(x+w)*8*z,(y+h)*8*z,outline='#72e7d3',width=2,dash=(4,2),tags='brush-cursor')
    def add_part(self,part):
        if not self.editable():return
        validate_part(part)
        if len(self.project.data.get('parts',[]))>=128:raise ValueError('Höchstens 128 eigene Bauteile pro Projekt.')
        self.project.begin('Bauteil merken');self.project.data.setdefault('parts',[]).append(part);self.project.commit()
        self.part_category.set('Eigene');self.refresh_parts();self.parts_gallery.selection_set(part['id']);self.tabs.select(self.terrain_tab);self.terrain_tabs.select(self.parts_tab)
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
        selected=self.monsters.selection();self.monsters.delete(*self.monsters.get_children());term=self.filter.get().casefold();self.monster_photos=[]
        for m in self.definitions:
            name=self.library_names.get(m['code'],'');label=m['code']+(' · Boss' if m['boss'] else '')+'\n'+(name or (f'{len(m["variants"])} Varianten' if len(m['variants'])>1 else 'Gegner auswählen'))
            if term in label.casefold():
                photo=ImageTk.PhotoImage(self.sprites.thumbnail(m,(round(58*self.ui),round(58*self.ui))));self.monster_photos.append(photo)
                self.monsters.insert('','end',iid=m['code'],text=label,image=photo)
        if selected and self.monsters.exists(selected[0]):self.monsters.selection_set(selected[0])
        else:
            self.monster_template=None;self.library_titles['Monster'].set('1. Bild auswählen');self.library_previews['Monster'].delete('all')
            for button in self.library_actions['Monster']:button.configure(state='disabled')
    def filter_objects(self):
        selected=self.object_picker.selection()
        monster_types={m['type'] for m in self.definitions}
        rows={f'object-{e["type"]:02x}-{e["variant"]:02x}':dict(e,name=f'O-{e["type"]:04X} · V{e["variant"]}') for e in self.catalog if e['type'] not in monster_types and e['type']!=0x17}
        rows['candle']=dict(type=14,variant=0x18,kind='candle',name='O-000E · Kerze')
        rows.update({p['id']:p for p in MOVING_PLATFORMS});self.object_rows=rows;self.object_photos=[]
        self.object_picker.delete(*self.object_picker.get_children())
        for key,row in rows.items():
            photo=ImageTk.PhotoImage(self.sprites.thumbnail(row,(round(58*self.ui),round(58*self.ui))));self.object_photos.append(photo)
            self.object_picker.insert('','end',iid=key,text=row['name']+(' · Grafik noch nicht erfasst' if not self.sprites.sprite(row) else '')+(' · Szenenobjekt' if row.get('kind')=='event' else ''),image=photo)
        if selected and self.object_picker.exists(selected[0]):self.object_picker.selection_set(selected[0])
        else:
            self.library_titles['Objekt'].set('1. Bild auswählen');self.library_previews['Objekt'].delete('all')
            for button in self.library_actions['Objekt']:button.configure(state='disabled')
    def choose_object(self,e=None):
        selection=self.object_picker.selection()
        if selection:
            self.object_template=copy.deepcopy(self.object_rows[selection[0]]);self.library_preview('Objekt',self.object_template)
    def select_object_template(self,row):
        self.object_template=copy.deepcopy(row);self.object_template.setdefault('name','');self.tool.set('Objekt');self.selected_object=None;self.object_props.pack_forget();self.refresh_brush()
        self.status.set((row.get('name') or self.actor_code(row))+' · Linksklick setzt die Figur · Esc beendet das Platzieren.')
    def actor_code(self,actor):return ('M-' if any(d['type']==actor['type'] for d in self.definitions) else 'O-')+f'{actor["type"]:04X}'
    def actor_label(self,actor):
        code=self.actor_code(actor);name=actor.get('name') or getattr(self,'library_names',{}).get(code,'');return code+(' · '+name if name else '')
    def actor_position(self,actor):
        if actor['type']>=128:
            from level_bosses import arena_floor
            entry=next((e for e in self.catalog if e['type']==actor['type']),actor)
            return actor['x'],arena_floor(self.current(),actor)+entry.get('y',96)-192
        return actor['x'],actor['y']
    def actor_bounds(self,actor):
        sprite=self.sprites.sprite(actor)
        if sprite:
            image,anchor=sprite;box=image.getbbox();x,y=self.actor_position(actor)
            return (x-anchor[0]+box[0],y-anchor[1]+box[1],x-anchor[0]+box[2],y-anchor[1]+box[3])
        return (actor['x']-12,actor['y']-16,actor['x']+12,actor['y']+16)
    def pixel_coords(self,e):return int(self.canvas.canvasx(e.x)//self.zoom.get()),int(self.canvas.canvasy(e.y)//self.zoom.get())
    def coords(self,e):
        x,y=self.pixel_coords(e);return x//8,y//8
    def hit_object(self,wx,wy):
        r=self.current();z=self.zoom.get();pad=max(1,4*self.ui/z)
        for actor in reversed(r['actors']):
            x1,y1,x2,y2=self.actor_bounds(actor)
            if x1-pad<=wx<x2+pad and y1-pad<=wy<y2+pad:return ('actor',actor['id'])
            label=self.canvas.bbox('actor-label-'+actor['id'])
            if label and label[0]<=wx*z<label[2] and label[1]<=wy*z<label[3]:return ('actor',actor['id'])
        for door in reversed(r['doors']):
            if door['x']<=wx<door['x']+door['w'] and door['y']<=wy<door['y']+door['h']:return ('door',door['id'])
        return None
    def press(self,e):
        self.canvas.focus_set()
        if self.original_view and (self.original_loading or self.original_room is None):return
        wx,wy=self.pixel_coords(e);x,y=wx//8,wy//8;r=self.current();tool=self.tool.get()
        if not 0<=x<r['width'] or not 0<=y<r['height']:return
        hit=self.hit_object(wx,wy) if tool in ('Auswahl','Monster','Objekt') and not getattr(e,'state',0)&8 else None
        self.start=(x,y);self.drag=(x,y);self.pixel_drag=(wx,wy);self.gesture='object' if hit else tool
        if hit:
            self.selected_object=hit;self.selection=None;item=self.object();self.object_drag_offset=(item['x']-wx,item['y']-wy)
            self.tool.set('Auswahl');self.canvas.configure(cursor='fleur');self.object_fields();self.schedule();return
        if tool=='Auswahl':
            self.selected_object=None;self.object_props.pack_forget();self.selection=(x,y,x,y);self.schedule();return
        if not self.ensure_editable():self.start=None;return
        r=self.current();self.project.begin(tool);self.selected_object=None
        if tool in ('Zeichnen','Bauteil','Kollision'):self.stamp(x,y)
        elif tool=='Fläche':self.selection=(x,y,x,y)
        elif tool=='Start':r['spawn']=[wx,wy]
        elif tool in ('Monster','Objekt'):
            row=self.library_entry(tool) or (self.monster_template if tool=='Monster' else self.object_template)
            if row:
                self.place_actor(row,wx,wy)
                if getattr(e,'state',0)&1:self.tool.set(tool)
            else:self.status.set('Rechts ein Bild auswählen und „Hinzufügen“ oder „Mit Maus platzieren“ wählen.')
        elif tool=='Ausgang':
            target=next((q for q in self.project.data['rooms'] if q['id']!=r['id']),r)
            d=dict(id='D-'+uuid.uuid4().hex[:8],x=wx,y=wy,w=32,h=48,target=target['id'],target_x=target['spawn'][0],target_y=target['spawn'][1],trigger='up')
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
        wx,wy=self.pixel_coords(e);x,y=wx//8,wy//8;self.hover=(x,y);tool=getattr(self,'gesture',self.tool.get())
        if tool=='object' and self.selected_object:
            if (wx,wy)==self.pixel_drag:return
            selected=self.selected_object
            if not self.ensure_editable():return
            self.selected_object=selected;r=self.current();item=self.object()
            if not item:return
            self.project.begin('Figur verschieben');ox,oy=self.object_drag_offset
            xx,yy=max(0,min(r['width']*8-1,wx+ox)),max(0,min(r['height']*8-1,wy+oy))
            if getattr(e,'state',0)&1:xx=min(r['width']*8-1,round(xx/8)*8);yy=min(r['height']*8-1,round(yy/8)*8)
            if item.get('kind')=='platform':
                xx=max(96 if item.get('variant',0)==0 else 16,min(r['width']*8-16,xx));yy=max(88 if item.get('variant',0)==1 else 8,min(r['height']*8-8,yy))
            item['x'],item['y']=xx,yy;self.object_fields();self.canvas.configure(cursor='fleur')
        elif tool in ('Zeichnen','Kollision'):
            ox,oy=self.drag;n=max(abs(x-ox),abs(y-oy),1)
            for i in range(n+1):self.stamp(round(ox+(x-ox)*i/n),round(oy+(y-oy)*i/n))
        elif tool in ('Fläche','Auswahl'):
            r=self.current();self.selection=(max(0,min(self.start[0],x)),max(0,min(self.start[1],y)),min(r['width']-1,max(self.start[0],x)),min(r['height']-1,max(self.start[1],y)))
        self.drag=(x,y);self.schedule()
    def release(self,e):
        if self.start is None:return
        if getattr(self,'gesture',None)=='Fläche' and self.selection and not self.original_view:
            x1,y1,x2,y2=self.selection;w=self.brush_width;h=max(1,len(self.brush)//w)
            for y in range(y1,y2+1,h):
                for x in range(x1,x2+1,w):paint(self.current(),self.layer.get(),x,y,self.brush,self.brush_collision if self.auto_collision.get() else None,w,mask=self.brush_mask)
        if not self.original_view:self.project.commit()
        self.start=None;self.pixel_drag=None;self.mode_changed();self.schedule()
    def pick(self,e):
        x,y=self.coords(e);r=self.current()
        if 0<=x<r['width'] and 0<=y<r['height']:
            self.brush=[bind(r['layers'][self.layer.get()][y*r['width']+x],r['tileset'],self.layer.get())];self.brush_collision=[r['collision'][self.layer.get()][y*r['width']+x]];self.brush_width=1;self.brush_mask=None;self.tool.set('Zeichnen');self.refresh_brush();self.status.set(f'Kachel mit Originalquelle aufgenommen: {self.brush[0]:08X}')
    def object(self):
        if not self.selected_object:return None
        kind,identifier=self.selected_object;return next((a for a in self.current()['actors' if kind=='actor' else 'doors'] if a['id']==identifier),None)
    def nudge_actor(self,dx,dy):
        if not self.ensure_editable():return
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
            self.object_props.pack(side='bottom',fill='x',pady=6,before=self.room_tabs)
            for k,v in self.props.items():v.set(str(item.get(k,'')))
            moving=self.selected_object[0]=='actor' and is_platform(item)
            actor=self.selected_object[0]=='actor'
            allowed={'name','x','y','variant','plane'}|({'motion'} if moving else set()) if actor else {'x','y','target','target_x','target_y','trigger','plane'}
            for key,widgets in self.prop_rows.items():
                for widget in widgets:
                    if key in allowed:widget.grid()
                    else:widget.grid_remove()
            self.object_props.configure(text=self.actor_code(item) if actor else 'Ausgang')
            self.prop_rows['plane'][0].configure(text='Spielebene' if actor else 'Zielebene');self.duplicate_button.configure(state='normal' if actor else 'disabled')
            if actor:self.details_button.grid()
            else:self.details_button.grid_remove()
            if actor and any(d['type']==item['type'] for d in self.definitions):self.animation_button.grid()
            else:self.animation_button.grid_remove()
            self.motion_box.configure(state='readonly' if moving else 'disabled');self.variant_entry.configure(state='readonly' if moving else 'normal')
            self.props['motion'].set(('Waagerecht' if item.get('variant',0)==0 else 'Senkrecht') if moving else '')
            self.props['plane'].set(('back' if item.get('flags',0)&0x8000==0 else 'front') if self.selected_object[0]=='actor' else ('back' if item.get('target_plane',0) else 'front'))
            if self.selected_object[0]=='actor':
                val=values_for(self.rom,item,self.current()['tileset']);self.actor_stats.set(f'HP: {val["hp"] if val["hp"] is not None else "Bossinitialisierung"} · Kontaktschaden: {val["contact_damage"]} · Trefferbereich: {val["half_width"]*2} × {val["half_height"]*2}')
            else:self.actor_stats.set('')
            if 'target' in item:
                target=self.project.get(item['target']);self.props['target'].set(target['id']+' · '+target['name'])
    def actor_details(self):
        if self.selected_object and not self.ensure_editable():return
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
            ttk.Label(box,text='direct: vorbereiteter Kampf · sequence: native Einleitung\ncontinue: Raum weiter erkunden · exit: erster Raumausgang nach dem Sieg\nDer Kampfboden folgt dem Boden unter dem Platzierungspunkt. Ein Bosskampf ist eine einzelne Begegnung mit fester Kamera; andere Gegner pausieren.',wraplength=round(610*self.ui)).pack(anchor='w',pady=6)
        entry=next((e for e in self.catalog if e['type']==item['type']),item)
        notes='Kerzen verwenden die native Objekt-KI; Variante steuert den Inhalt (Original-Byte, dezimal).' if item['type']==14 else 'Szenenobjekt als Kulisse: Die gemessene Originalgrafik wird an dieser Position dargestellt. Sein Original-Levelskript läuft im freien Leveltest nicht mit, da es fremde Kameras, Grafiken oder Levelwechsel auslösen kann. Interaktive Abläufe benötigen einen eigenen geprüften Adapter.' if item.get('kind')=='event' else ai_notes(entry)
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
        if not self.ensure_editable():return
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
        if not self.ensure_editable():return
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
            self.select_object_template(self.actor_clipboard);return
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
        if self.studio.visible:return
        if self.editable():self.project.undo();self.selected_object=None;self.refresh_rooms()
    def redo(self):
        if self.studio.visible:return
        if self.editable():self.project.redo();self.selected_object=None;self.refresh_rooms()
    def confirm(self):return not self.project.dirty or messagebox.askyesno('Ungespeicherte Änderungen','Ohne Speichern fortfahren?',parent=self.root)
    def new(self):
        if self.confirm():self.workspaces.select(self.level_page);self.original_view=False;self.generation+=1;self.project=Project();self.room_id=self.project.data['rooms'][0]['id'];self.room_tabs.select(self.project_tab);self.refresh_rooms();self.load_asset(0)
    def open(self):
        if not self.confirm():return
        name=filedialog.askopenfilename(parent=self.root,initialdir=self.project_directory(),filetypes=[('Castlevania-Level','*.sc4level.json'),('JSON','*.json')])
        if name:
            try:self.project=Project.load(name);self.workspaces.select(self.level_page);self.original_view=False;self.generation+=1;self.room_id=self.project.data['start_room'];self.room_tabs.select(self.project_tab);self.refresh_rooms();self.load_asset(self.current()['tileset'])
            except Exception as e:messagebox.showerror('Öffnen',str(e),parent=self.root)
    def save(self,as_new=False):
        if self.studio.visible and not as_new:self.studio.save();return
        if self.original_view and not self.edit_original():return
        name=self.project.path
        if as_new or name is None:name=filedialog.asksaveasfilename(parent=self.root,initialdir=self.project_directory(),defaultextension='.sc4level.json',initialfile='Mein_Level.sc4level.json',filetypes=[('Castlevania-Level','*.sc4level.json')])
        if name:
            try:self.project.save(name);self.status.set('Projekt gespeichert: '+str(name));self.schedule()
            except Exception as e:messagebox.showerror('Speichern',str(e),parent=self.root)
    def project_directory(self):
        path=self.project.path.parent if self.project.path else ROOT/'artwork-local/level-editor/projects';path.mkdir(parents=True,exist_ok=True);return path
    def test(self):
        if self.studio.visible:
            if self.studio.workshop:self.studio.workshop.spawn()
            return
        if self.play_pending:return
        if self.playtest:self.stop_test()
        parent=ROOT/'artwork-local/level-editor/tests';parent.mkdir(parents=True,exist_ok=True);folder=Path(tempfile.mkdtemp(prefix='play-',dir=parent));data=copy.deepcopy(self.project.data)
        if not self.original_view:data['start_room']=self.room_id
        self.play_pending=True;scale=round(3*self.ui);self.status.set('Bossbegegnungen werden bei Bedarf einmalig vorbereitet; danach startet der Spieltest …' if not self.original_view and any(a['type']>=128 for r in data['rooms'] for a in r['actors']) else 'Spieltest wird vorbereitet …')
        if self.original_view:
            number=self.original_number;self.background(lambda:('play',OriginalPlaytest(number,folder,window_scale=scale)))
        else:self.background(lambda:('play',Playtest(data,folder,window_scale=scale)))
    def stop_test(self):
        if hasattr(self,'studio') and self.studio.visible:self.studio.pause();return
        self.stop_level_test()
    def stop_level_test(self):
        if self.playtest:self.playtest.close();self.playtest=None;self.status.set('Spieltest beendet. Dein Projekt bleibt geöffnet.')
    def close(self):
        if not self.confirm():return
        if not self.studio.close():return
        self.closing=True
        for timer in (self.tick_id,self.draw_id):
            if timer:self.root.after_cancel(timer)
        self.stop_level_test();self.root.withdraw();self.finish_close()
    def finish_close(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='ok' and value[0]=='play':value[1].close()
        except queue.Empty:pass
        if any(t.is_alive() for t in self.workers) or not self.studio.stopped():self.root.after(100,self.finish_close)
        else:self.root.destroy()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',type=Path);parser.add_argument('--demo',action='store_true');parser.add_argument('--monsters',action='store_true');args=parser.parse_args()
    if args.demo and args.project is None:
        from level_demo import make_demo
        args.project=make_demo()
    root=tk.Tk();app=Editor(root,Project.load(args.project) if args.project else None)
    if args.monsters:root.after_idle(app.open_monster_workshop)
    root.mainloop()
