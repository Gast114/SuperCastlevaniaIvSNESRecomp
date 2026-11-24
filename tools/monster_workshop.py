"""Monster-first native test arena, action library and live HD artwork studio."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import zipfile

from PIL import Image, ImageTk
from enemy_workshop import Worker, preview, pose_preview, DEFAULT_WORKSPACE
from enemy_workshop_assets import Workspace
from enemy_workshop_library import DEFAULT_LIBRARY, profile_key
from enemy_workshop_native import ROOT
from monster_model import GROUPS, actions, ai_notes, code, combat_stats, definitions, frame_groups, visible_frames


# ── Dark-Gothic Castlevania Studio Palette ───────────────────────────────────
BG_APP      = '#0d1017'   # Deep obsidian canvas
BG_PANEL    = '#141923'   # Elevated slate card
BG_SURFACE  = '#10151e'   # Input / treeview surface
BG_HOVER    = '#1d2536'   # Interactive hover
BG_SELECTED = '#2c2230'   # Selected row (muted wine-slate)
BORDER      = '#263043'   # Hairline border
GOLD        = '#d4af5a'   # Antique burnished gold (headers, HD badges)
GOLD_DIM    = '#8f7539'   # Subtle gold accent
CRIMSON     = '#992536'   # Gothic crimson primary action
CRIMSON_HOV = '#b62d41'
EMERALD     = '#3fb97c'   # HD Active indicator
TEXT        = '#eef2f7'   # Crisp ivory-white
TEXT_MUTED  = '#8e9cb2'   # Secondary labels

ZOOM_OPTIONS = {
    '1× Arena':  1.0,
    '2× Nah':    2.0,
    '2.5× Fokus': 2.5,
    '3.5× Groß': 3.5,
    '4.5× Detail': 4.5,
}
BACKDROP_OPTIONS = {
    'Gothic':      'gothic',
    'Dunkel':      'dark',
    'Schachbrett': 'checker',
}


def apply_gothic_theme(root, scale=1.0):
    """Apply a cohesive Dark-Gothic Studio ttk theme without breaking embedded hosts."""
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass
    root.configure(bg=BG_APP)
    base_pt = max(9, round(10 * min(scale, 1.2)))
    small_pt = max(8, round(9 * min(scale, 1.2)))
    title_pt = max(14, round(17 * min(scale, 1.2)))
    h2_pt = max(10, round(11 * min(scale, 1.2)))

    style.configure('.', background=BG_APP, foreground=TEXT, fieldbackground=BG_SURFACE,
                    bordercolor=BORDER, darkcolor=BG_APP, lightcolor=BG_PANEL,
                    troughcolor=BG_SURFACE, font=('Segoe UI', base_pt))
    style.configure('TFrame', background=BG_APP)
    style.configure('Card.TFrame', background=BG_PANEL)
    style.configure('Header.TFrame', background='#0a0d13')
    style.configure('TLabel', background=BG_APP, foreground=TEXT)
    style.configure('Card.TLabel', background=BG_PANEL, foreground=TEXT)
    style.configure('Muted.TLabel', background=BG_APP, foreground=TEXT_MUTED, font=('Segoe UI', small_pt))
    style.configure('CardMuted.TLabel', background=BG_PANEL, foreground=TEXT_MUTED, font=('Segoe UI', small_pt))
    style.configure('Title.TLabel', background='#0a0d13', foreground=GOLD, font=('Georgia', title_pt, 'bold'))
    style.configure('Subtitle.TLabel', background='#0a0d13', foreground=TEXT_MUTED, font=('Segoe UI', small_pt))
    style.configure('Section.TLabel', background=BG_PANEL, foreground=GOLD, font=('Segoe UI', h2_pt, 'bold'))
    style.configure('BadgeHD.TLabel', background='#173025', foreground=EMERALD, font=('Segoe UI', small_pt, 'bold'), padding=(8, 3))
    style.configure('BadgeSD.TLabel', background='#1e2533', foreground=TEXT_MUTED, font=('Segoe UI', small_pt), padding=(8, 3))

    style.configure('TLabelframe', background=BG_PANEL, bordercolor=BORDER, relief='solid', borderwidth=1)
    style.configure('TLabelframe.Label', background=BG_PANEL, foreground=GOLD, font=('Segoe UI', base_pt, 'bold'))
    style.configure('Stage.TLabelframe', background='#0b0e14', bordercolor=GOLD_DIM, relief='solid', borderwidth=1)
    style.configure('Stage.TLabelframe.Label', background='#0b0e14', foreground=GOLD, font=('Segoe UI', base_pt, 'bold'))

    style.configure('TButton', background='#1c2433', foreground=TEXT, bordercolor=BORDER,
                    focuscolor=GOLD_DIM, padding=(10, 5), relief='flat')
    style.map('TButton',
              background=[('disabled', '#131822'), ('pressed', '#273247'), ('active', '#253045')],
              foreground=[('disabled', '#4e5a6e'), ('active', '#ffffff')],
              bordercolor=[('active', GOLD_DIM)])

    style.configure('Crimson.TButton', background=CRIMSON, foreground='#ffffff', bordercolor='#b8384a',
                    font=('Segoe UI', base_pt, 'bold'), padding=(12, 6), relief='flat')
    style.map('Crimson.TButton',
              background=[('disabled', '#3a1a20'), ('pressed', '#7a1c2a'), ('active', CRIMSON_HOV)],
              foreground=[('disabled', '#8a686e')])

    style.configure('Gold.TButton', background='#2c2414', foreground=GOLD, bordercolor=GOLD_DIM,
                    font=('Segoe UI', base_pt, 'bold'), padding=(10, 5), relief='flat')
    style.map('Gold.TButton',
              background=[('disabled', '#171510'), ('active', '#3d321c')],
              foreground=[('disabled', '#5c5035'), ('active', '#f3d483')])

    style.configure('TCheckbutton', background=BG_APP, foreground=TEXT, indicatorcolor=BG_SURFACE,
                    indicatorrelief='flat', padding=(4, 2))
    style.map('TCheckbutton',
              background=[('active', BG_APP)],
              indicatorcolor=[('selected', GOLD), ('active', BG_HOVER)])
    style.configure('Card.TCheckbutton', background=BG_PANEL, foreground=TEXT, indicatorcolor=BG_SURFACE)
    style.map('Card.TCheckbutton',
              background=[('active', BG_PANEL)],
              indicatorcolor=[('selected', GOLD)])

    style.configure('TEntry', fieldbackground=BG_SURFACE, foreground=TEXT, insertcolor=GOLD,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, padding=(6, 4))
    style.map('TEntry', bordercolor=[('focus', GOLD)])

    style.configure('TCombobox', fieldbackground=BG_SURFACE, background='#1c2433', foreground=TEXT,
                    arrowcolor=GOLD, bordercolor=BORDER, padding=(5, 4))
    style.map('TCombobox',
              fieldbackground=[('readonly', BG_SURFACE)],
              foreground=[('readonly', TEXT)],
              selectbackground=[('readonly', BG_SURFACE)],
              selectforeground=[('readonly', TEXT)],
              bordercolor=[('focus', GOLD)])

    style.configure('TNotebook', background=BG_APP, bordercolor=BORDER, tabmargins=[0, 2, 0, 0])
    style.configure('TNotebook.Tab', background='#131823', foreground=TEXT_MUTED,
                    padding=(12, 6), bordercolor=BORDER, font=('Segoe UI', small_pt, 'bold'))
    style.map('TNotebook.Tab',
              background=[('selected', BG_PANEL), ('active', BG_HOVER)],
              foreground=[('selected', GOLD), ('active', TEXT)])

    style.configure('Treeview', background=BG_SURFACE, fieldbackground=BG_SURFACE, foreground=TEXT,
                    bordercolor=BORDER, rowheight=round(28 * scale))
    style.configure('Treeview.Heading', background='#181f2c', foreground=GOLD,
                    bordercolor=BORDER, relief='flat', font=('Segoe UI', small_pt, 'bold'))
    style.map('Treeview.Heading', background=[('active', BG_HOVER)])
    style.map('Treeview', background=[('selected', BG_SELECTED)], foreground=[('selected', '#ffffff')])
    style.configure('MonsterList.Treeview', background=BG_SURFACE, fieldbackground=BG_SURFACE,
                    foreground=TEXT, rowheight=round(54 * scale))

    style.configure('TPanedwindow', background=BG_APP)
    style.configure('Sash', sashthickness=5, sashrelief='flat', background=BORDER)
    style.configure('Vertical.TScrollbar', background='#1c2433', troughcolor=BG_SURFACE,
                    bordercolor=BG_SURFACE, arrowcolor=TEXT_MUTED)
    style.map('Vertical.TScrollbar', background=[('active', '#2b374d')])
    return style


def export_monster(workspace,entry,destination,extra_ids=(),graphics_variants=False):
    """A self-contained editable collection with code names and exact mappings."""
    groups=frame_groups(entry,workspace,extra_ids);frames={};members={};names={};baselines={}
    if not graphics_variants:
        poses=visible_frames(groups);parts=visible_frames(groups,components=True)
        groups={group:poses[group]+parts[group] for group in groups}
    for group,rows in groups.items():
        members[group]=[]
        for frame in rows:
            identifier=frame['id'];members[group].append(identifier)
            if identifier in frames:continue
            old=frame['image']
            if old not in names:
                role='Teil' if frame['component'] else 'Pose'
                names[old]=f'{code(entry["type"])}_{role}_{frame["pose"]:04X}_{hashlib.sha256(old.encode()).hexdigest()[:8]}.png'
            name=names[old]
            frames[identifier]=dict(frame,image=name,reference=name,label=f'P-{frame["pose"]:04X}')
            if old in workspace.data['work_templates']:baselines[name]=workspace.data['work_templates'][old]
    if not frames:raise ValueError('Für dieses Monster sind noch keine PNGs aufgenommen.')
    project=dict(version=1,name=code(entry['type']),frames=list(frames.values()),work_templates=baselines,
                 monster_names=workspace.data.get('monster_names',{}),monster_actions={profile_key(entry):members})
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('project.json',json.dumps(project,ensure_ascii=False,indent=2))
        archive.writestr('AKTIONEN.json',json.dumps(members,ensure_ascii=False,indent=2))
        archive.writestr('HIER_STARTEN.txt','Nur PNGs in artwork bearbeiten. Transparente Bildfläche und Dateinamen behalten.\n'
            'AKTIONEN.json ordnet die PNG-IDs ihren Aktionen zu. Geschosse gehören zum Angriff des Monsters.\n'
            'Die Zuordnung ist nur im ausgewiesenen Umfang geprüft. references und project.json aufbewahren.\n'
            'Den entpackten Ordner kannst du im HD-Import als Gegnerprojekt verwenden.\n')
        for old,name in names.items():
            reference=next(f['reference'] for f in workspace.frames.values() if f['image']==old)
            archive.write(workspace.folder/'artwork'/old,'artwork/'+name)
            archive.write(workspace.folder/'references'/reference,'references/'+name)
    return len(names)


class MonsterWorkshop:
    def __init__(self,root,rom=None,build=None,workspace=DEFAULT_WORKSPACE,library=DEFAULT_LIBRARY,*,embedded=False,catalog=None,initial_entry=None,on_place=None,on_values=None,on_name_changed=None,on_selected=None):
        self.root=root;self.embedded=embedded;self.on_place=on_place;self.on_values=on_values;self.on_name_changed=on_name_changed;self.on_selected=on_selected
        self.active=True;self.closed=False;self.tick_id=None
        self.runtime_args=(rom,build,library)
        self.workspace=workspace if isinstance(workspace,Workspace) else Workspace(workspace)
        if library and (Path(library)/'library.json').is_file():self.workspace.load_library(library)
        self.rom=Path(rom or ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
        self.commands=queue.Queue();self.events=queue.Queue(maxsize=8)
        self.catalog=list(catalog or []);self.monsters=definitions(self.catalog,self.rom);self.entry=dict(initial_entry or {'type':18,'variant':0})
        self.snapshot={'actors':[]};self.references=None;self.allowed=set();self.live_ids={}
        self.selected_id=None;self.signature=None;self.photos=[];self.closing=False
        self.last_ingest=0.;self.last_save=0.;self.dirty=False;self.active_action='Natürlich'
        self.hd_counts=self._scan_hd_actors()

        # Reactive Tk variables
        self.name=tk.StringVar(root);self.variant=tk.StringVar(root);self.parts=tk.BooleanVar(root,value=False)
        self.paused=tk.BooleanVar(root,value=False);self.still=tk.BooleanVar(root,value=False)
        self.speed=tk.StringVar(root,value='100%');self.show_bosses=tk.BooleanVar(root,value=True if not embedded else True)
        self.only_hd=tk.BooleanVar(root,value=False);self.search_var=tk.StringVar(root)
        self.graphics_variants=tk.BooleanVar(root,value=False)
        self.preview_mode=tk.StringVar(root,value='Normal')
        self.zoom_label=tk.StringVar(root,value='2.5× Fokus')
        self.backdrop_label=tk.StringVar(root,value='Gothic')
        self.hd_badge=tk.StringVar(root,value='Original 1×')
        self.monster_title=tk.StringVar(root,value='—')
        self.status=tk.StringVar(root,value='Eigene Original-Laufzeit startet …')
        self.context=tk.StringVar(root,value='Monster wählen, Aktionen prüfen, Original & HD-Redesign live vergleichen.')
        self.stats=tk.StringVar(root);self.notes=tk.StringVar(root);self.file=tk.StringVar(root);self.level_context=tk.StringVar(root)

        scale=max(1.,float(root.tk.call('tk','scaling'))/(96/72),min(root.winfo_screenwidth()/1920,root.winfo_screenheight()/1080))
        if embedded:scale=max(1.,float(root.tk.call('tk','scaling'))/(96/72))
        self.scale=scale
        if not embedded:
            root.title('Monster-Werkstatt · Super Castlevania IV HD Studio')
            root.tk.call('tk','scaling',96/72*scale)
            sw,sh=root.winfo_screenwidth(),root.winfo_screenheight()
            root.geometry(f'{min(round(1720*scale),sw-40)}x{min(round(1020*scale),sh-60)}')
            root.minsize(min(round(1180*scale),sw-60),min(round(740*scale),sh-80))
            apply_gothic_theme(root,scale)

        # ── Top Studio Header ────────────────────────────────────────────────
        if not embedded:
            header=ttk.Frame(root,style='Header.TFrame',padding=(18,10))
            header.pack(fill='x')
            title_col=ttk.Frame(header,style='Header.TFrame');title_col.pack(side='left')
            ttk.Label(title_col,text='MONSTER-WERKSTATT',style='Title.TLabel').pack(anchor='w')
            ttk.Label(title_col,text='Super Castlevania IV · Live-Original vs. HD-Redesign & Bestiary',style='Subtitle.TLabel').pack(anchor='w')
            hdr_right=ttk.Frame(header,style='Header.TFrame');hdr_right.pack(side='right')
            self.hd_badge_lbl=ttk.Label(hdr_right,textvariable=self.hd_badge,style='BadgeSD.TLabel')
            self.hd_badge_lbl.pack(side='left',padx=(0,14))
            ttk.Label(hdr_right,text='Zoom:',style='Subtitle.TLabel').pack(side='left',padx=(0,4))
            zoom_box=ttk.Combobox(hdr_right,textvariable=self.zoom_label,values=list(ZOOM_OPTIONS),state='readonly',width=12)
            zoom_box.pack(side='left',padx=(0,12))
            ttk.Label(hdr_right,text='Bühne:',style='Subtitle.TLabel').pack(side='left',padx=(0,4))
            bg_box=ttk.Combobox(hdr_right,textvariable=self.backdrop_label,values=list(BACKDROP_OPTIONS),state='readonly',width=11)
            bg_box.pack(side='left')
            tk.Frame(root,bg=GOLD_DIM,height=1).pack(fill='x')
        else:
            self.hd_badge_lbl=None

        outer=ttk.Frame(root,padding=(12,10,12,8));outer.pack(fill='both',expand=True)
        if embedded:
            link=ttk.Frame(outer);link.pack(fill='x',pady=(0,8))
            self.place_button=ttk.Button(link,text='＋ Im Level hinzufügen',style='Crimson.TButton',command=lambda:self.on_place(self.entry));self.place_button.pack(side='right')
            self.values_button=ttk.Button(link,text='Werte der Level-Figur…',command=lambda:self.on_values(self.entry),state='disabled');self.values_button.pack(side='right',padx=8)
            ttk.Label(link,textvariable=self.level_context,wraplength=round(620*scale)).pack(side='left',fill='x',expand=True)

        # ── Main 3-Column Studio Split ───────────────────────────────────────
        split=ttk.Panedwindow(outer,orient='horizontal');split.pack(fill='both',expand=True)
        left=ttk.Frame(split,width=round(300*scale),style='Card.TFrame',padding=10)
        center=ttk.Frame(split,padding=(8,0))
        right=ttk.Frame(split,width=round(360*scale),style='Card.TFrame',padding=10)
        split.add(left,weight=0);split.add(center,weight=4);split.add(right,weight=0)

        # ── LEFT: Monster & Boss Browser ─────────────────────────────────────
        ttk.Label(left,text='MONSTER & BOSSE',style='Section.TLabel').pack(anchor='w',pady=(0,6))
        search_row=ttk.Frame(left,style='Card.TFrame');search_row.pack(fill='x',pady=(0,6))
        search_entry=ttk.Entry(search_row,textvariable=self.search_var)
        search_entry.pack(side='left',fill='x',expand=True)
        self.search_var.trace_add('write',lambda *_:self.refresh_monsters())
        ttk.Button(search_row,text='✕',width=3,command=lambda:self.search_var.set('')).pack(side='left',padx=(4,0))

        filter_row=ttk.Frame(left,style='Card.TFrame');filter_row.pack(fill='x',pady=(0,6))
        ttk.Checkbutton(filter_row,text='Bosse',variable=self.show_bosses,style='Card.TCheckbutton',command=self.refresh_monsters).pack(side='left')
        ttk.Checkbutton(filter_row,text='✦ Nur HD',variable=self.only_hd,style='Card.TCheckbutton',command=self.refresh_monsters).pack(side='left',padx=(10,0))

        from level_objects import SpriteLibrary
        self.sprite_library=SpriteLibrary(ROOT/'artwork-local/enemy-library');self.picker_photos=[]
        list_wrap=ttk.Frame(left,style='Card.TFrame');list_wrap.pack(fill='both',expand=True,pady=(0,8))
        self.picker=ttk.Treeview(list_wrap,show='tree',selectmode='browse',height=12,style='MonsterList.Treeview')
        self.picker.column('#0',width=round(265*scale),stretch=True)
        scrollbar=ttk.Scrollbar(list_wrap,command=self.picker.yview);self.picker.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y');self.picker.pack(fill='both',expand=True)
        self.picker.bind('<<TreeviewSelect>>',self.choose)

        # Compact Name / Variant / Spawn Controls
        ctrl_card=ttk.Frame(left,style='Card.TFrame');ctrl_card.pack(fill='x')
        ttk.Label(ctrl_card,text='Anzeigename',style='CardMuted.TLabel').pack(anchor='w')
        name_row=ttk.Frame(ctrl_card,style='Card.TFrame');name_row.pack(fill='x',pady=(2,6))
        ttk.Entry(name_row,textvariable=self.name).pack(side='left',fill='x',expand=True)
        ttk.Button(name_row,text='✓',width=3,style='Gold.TButton',command=self.save_name).pack(side='left',padx=(4,0))

        var_row=ttk.Frame(ctrl_card,style='Card.TFrame');var_row.pack(fill='x',pady=(0,8))
        ttk.Label(var_row,text='Variante:',style='CardMuted.TLabel').pack(side='left',padx=(0,6))
        self.variants=ttk.Combobox(var_row,textvariable=self.variant,state='readonly',width=14)
        self.variants.pack(side='left',fill='x',expand=True);self.variants.bind('<<ComboboxSelected>>',self.change_variant)

        ttk.Button(ctrl_card,text='▶  Spawnen / Neu starten',style='Crimson.TButton',command=self.spawn).pack(fill='x')

        # ── CENTER: Vertical Split (HUGE 72% Preview Stage + 28% Poses) ──────
        vsplit=ttk.Panedwindow(center,orient='vertical');vsplit.pack(fill='both',expand=True)
        stage_wrap=ttk.Frame(vsplit);poses_wrap=ttk.Frame(vsplit)
        vsplit.add(stage_wrap,weight=5);vsplit.add(poses_wrap,weight=2)

        # Huge Side-by-Side Live Preview Canvases
        views=ttk.Frame(stage_wrap);views.pack(fill='both',expand=True);self.canvases=[]
        for title in ('ORIGINAL  ·  SNES 1×','HD-REDESIGN  ·  LIVE'):
            box=ttk.LabelFrame(views,text=f'  {title}  ',style='Stage.TLabelframe',padding=4)
            box.pack(side='left',fill='both',expand=True,padx=4)
            canvas=tk.Canvas(box,background='#0b0e14',highlightthickness=0,width=420,height=420)
            canvas.pack(fill='both',expand=True);self.canvases.append(canvas)

        # Playback & Quick-Action Transport Bar
        controls=ttk.Frame(stage_wrap,style='Card.TFrame',padding=(10,6));controls.pack(fill='x',pady=(6,2))
        ttk.Checkbutton(controls,text='⏸ Pause',variable=self.paused,style='Card.TCheckbutton',command=lambda:self.send('pause',value=self.paused.get())).pack(side='left')
        ttk.Button(controls,text='⏭ Ein Feld',command=self.single_step).pack(side='left',padx=(8,4))
        speed_box=ttk.Combobox(controls,textvariable=self.speed,values=['25%','50%','100%'],state='readonly',width=6)
        speed_box.pack(side='left',padx=(0,10));speed_box.bind('<<ComboboxSelected>>',lambda _:self.send('speed',value=float(self.speed.get().strip('%'))/100))
        ttk.Button(controls,text='◀ Ziel links',command=lambda:self.send('direction',value='Links')).pack(side='left',padx=2)
        ttk.Button(controls,text='Ziel rechts ▶',command=lambda:self.send('direction',value='Rechts')).pack(side='left',padx=(2,10))
        ttk.Button(controls,text='↺ Natürlich',style='Gold.TButton',command=lambda:self.run_action('Natürlich')).pack(side='left',padx=2)
        if embedded:
            ttk.Label(controls,text='Zoom:',style='CardMuted.TLabel').pack(side='right',padx=(6,2))
            ttk.Combobox(controls,textvariable=self.zoom_label,values=list(ZOOM_OPTIONS),state='readonly',width=11).pack(side='right')

        # Bottom Pose & Action Library Notebook
        self.tabs=ttk.Notebook(poses_wrap);self.tabs.pack(fill='both',expand=True,pady=(4,0))
        self.trees={};self.buttons={};self.hints={}
        for group in GROUPS:
            panel=ttk.Frame(self.tabs,style='Card.TFrame',padding=6);self.tabs.add(panel,text=group)
            bar=ttk.Frame(panel,style='Card.TFrame');bar.pack(fill='x',pady=(0,4))
            action={'Gehen / Bewegen':'Gehen'}.get(group,group)
            button=ttk.Button(bar,text='▶ Aktion abspielen',style='Gold.TButton',command=lambda a=action:self.run_action(a))
            if group!='Noch zuordnen':button.pack(side='left');self.buttons[group]=button
            hint=tk.StringVar();self.hints[group]=hint
            ttk.Label(bar,textvariable=hint,style='CardMuted.TLabel',wraplength=round(520*scale)).pack(side='left',padx=10)
            t_wrap=ttk.Frame(panel,style='Card.TFrame');t_wrap.pack(fill='both',expand=True)
            tree=ttk.Treeview(t_wrap,columns=('role','source'),show='tree headings',height=4,selectmode='browse')
            tree.heading('#0',text='Posen-Code');tree.column('#0',width=145)
            tree.heading('role',text='Bestandteil');tree.column('role',width=170)
            tree.heading('source',text='Zuordnung');tree.column('source',width=165)
            scroll=ttk.Scrollbar(t_wrap,command=tree.yview);tree.configure(yscrollcommand=scroll.set)
            scroll.pack(side='right',fill='y');tree.pack(fill='both',expand=True)
            tree.bind('<<TreeviewSelect>>',lambda event,t=tree:self.select_pose(t));self.trees[group]=tree
        self.tabs.bind('<<NotebookTabChanged>>',self.tab_changed)

        edit=ttk.Frame(poses_wrap,padding=(2,5,2,0));edit.pack(fill='x')
        ttk.Checkbutton(edit,text='Einzelteile',variable=self.parts,command=self.invalidate).pack(side='left')
        ttk.Checkbutton(edit,text='Grafikvarianten',variable=self.graphics_variants,command=self.invalidate).pack(side='left',padx=(6,0))
        ttk.Checkbutton(edit,text='PNG groß einzeln ansehen',variable=self.still,command=self.still_changed).pack(side='left',padx=(8,10))
        ttk.Button(edit,text='PNG öffnen',command=self.open_png).pack(side='left',padx=(0,4))
        ttk.Button(edit,text='PNG ersetzen…',style='Gold.TButton',command=self.replace).pack(side='left')
        ttk.Label(poses_wrap,textvariable=self.file,style='Muted.TLabel',wraplength=round(760*scale)).pack(anchor='w',pady=(2,0))

        # ── RIGHT: Bestiary Lore & Combat Stats Inspector ────────────────────
        ttk.Label(right,textvariable=self.monster_title,style='Section.TLabel',wraplength=round(330*scale)).pack(anchor='w',pady=(0,6))
        details=ttk.Notebook(right);details.pack(fill='both',expand=True,pady=(0,8))

        # Tab 1: Castlevania Wiki Bestiary & Lore (visible by default!)
        lore_panel=ttk.Frame(details,style='Card.TFrame',padding=10)
        details.add(lore_panel,text='Bestiary & Wiki')
        self.notes_text=tk.Text(lore_panel,wrap='word',bg=BG_SURFACE,fg=TEXT,relief='flat',
                                borderwidth=0,highlightthickness=1,highlightbackground=BORDER,
                                font=('Segoe UI',max(9,round(10*min(scale,1.15)))),padx=10,pady=8,height=12)
        notes_scroll=ttk.Scrollbar(lore_panel,command=self.notes_text.yview)
        self.notes_text.configure(yscrollcommand=notes_scroll.set,state='disabled')
        notes_scroll.pack(side='right',fill='y')
        self.notes_text.pack(fill='both',expand=True,pady=(0,8))
        ttk.Label(lore_panel,text='TESTRAUM-KONTEXT',style='Section.TLabel').pack(anchor='w',pady=(2,2))
        ttk.Label(lore_panel,textvariable=self.context,style='CardMuted.TLabel',justify='left',wraplength=round(315*scale)).pack(anchor='w',fill='x')

        # Tab 2: Combat Stats (Normal vs NG+)
        stats_panel=ttk.Frame(details,style='Card.TFrame',padding=10)
        details.add(stats_panel,text='Kampfwerte')
        ttk.Label(stats_panel,text='Werte aus dem Original',style='Section.TLabel').pack(anchor='w',pady=(0,6))
        self.comparison=ttk.Treeview(stats_panel,columns=('stat','normal','ng'),show='headings',height=2,selectmode='none')
        for key,label,width in (('stat','Startwert',120),('normal','Normal',66),('ng','New Game+',88)):
            self.comparison.heading(key,text=label);self.comparison.column(key,width=round(width*scale),stretch=True)
        self.comparison.insert('','end',iid='hp',values=('Gesundheit','—','—'))
        self.comparison.insert('','end',iid='contact',values=('Kontaktschaden','—','—'))
        self.comparison.pack(fill='x',pady=(0,8))
        mode_row=ttk.Frame(stats_panel,style='Card.TFrame');mode_row.pack(fill='x',pady=(0,8))
        ttk.Label(mode_row,text='Vorschau:',style='CardMuted.TLabel').pack(side='left',padx=(0,6))
        mode_box=ttk.Combobox(mode_row,textvariable=self.preview_mode,values=['Normal','New Game+'],state='readonly',width=14)
        mode_box.pack(side='left');mode_box.bind('<<ComboboxSelected>>',self.change_mode)
        ttk.Label(stats_panel,textvariable=self.stats,style='Card.TLabel',justify='left',wraplength=round(315*scale)).pack(anchor='w')

        # Bottom Export / Pack Buttons
        ttk.Button(right,text='Monster als PNG-Set exportieren',command=self.export).pack(fill='x',pady=(0,4))
        ttk.Button(right,text='✦ HD-Paket erstellen',style='Gold.TButton',command=self.build_pack).pack(fill='x',pady=(0,4))
        ttk.Button(right,text='Arbeitsordner öffnen',command=lambda:os.startfile(self.workspace.folder)).pack(fill='x')

        # Bottom Status Bar
        ttk.Label(outer,textvariable=self.status,style='Muted.TLabel',wraplength=round(1500*scale)).pack(anchor='w',pady=(6,0))

        self.worker=Worker(self.commands,self.events,rom,build,arena=True,library=library,initial_entry=initial_entry);self.worker.start()
        if not embedded:root.protocol('WM_DELETE_WINDOW',self.close)
        if self.catalog:self.select_entry(self.entry,spawn=False)
        self.tick_id=root.after(50,self.tick)

    def _scan_hd_actors(self):
        """Fast scan of which actor_types have HD artwork (size differs from 1x reference)."""
        counts={}
        art_dir=self.workspace.folder/'artwork'
        ref_dir=self.workspace.folder/'references'
        seen_img={}
        for frame in self.workspace.frames.values():
            if frame.get('component'):continue
            img=frame['image']
            if img not in seen_img:
                ap=art_dir/img;rp=ref_dir/frame['reference']
                try:
                    if ap.is_file() and rp.is_file():
                        with Image.open(ap) as im_a, Image.open(rp) as im_r:
                            seen_img[img]=im_a.size!=im_r.size or ap.stat().st_size!=rp.stat().st_size
                    else:seen_img[img]=False
                except OSError:seen_img[img]=False
            if seen_img[img]:
                at=frame['actor_type']
                counts[at]=counts.get(at,0)+1
        return counts

    def _set_notes_text(self,text):
        self.notes.set(text)
        self.notes_text.configure(state='normal')
        self.notes_text.delete('1.0','end')
        self.notes_text.insert('1.0',text)
        self.notes_text.configure(state='disabled')

    def send(self,kind,**values):self.commands.put(dict(kind=kind,**values))
    def invalidate(self):self.signature=None

    def refresh_monsters(self):
        selected=self.picker.selection();current=selected[0] if selected else code(self.entry['type'])
        self.picker.delete(*self.picker.get_children())
        names=self.workspace.data.get('monster_names',{});self.picker_photos=[]
        query=self.search_var.get().strip().lower()
        for monster in self.monsters:
            if monster['boss'] and not self.show_bosses.get():continue
            c=monster['code'];name=names.get(c,'')
            has_hd=self.hd_counts.get(monster['type'],0)>0
            if self.only_hd.get() and not has_hd:continue
            label=f'{name}  ({c})' if name else c
            if has_hd:label='✦ '+label
            if query and query not in label.lower() and query not in c.lower():continue
            photo=ImageTk.PhotoImage(self.sprite_library.thumbnail(monster,(round(50*self.scale),round(44*self.scale))),master=self.root);self.picker_photos.append(photo)
            self.picker.insert('','end',iid=c,text=' '+label,image=photo)
        if self.picker.exists(current):self.picker.selection_set(current)

    def choose(self,*_):
        selection=self.picker.selection()
        if not selection:return
        monster=next(m for m in self.monsters if m['code']==selection[0])
        if self.entry.get('_chosen') and self.entry['type']==monster['type']:return
        self.entry=dict(monster['variants'][0],_chosen=True)
        self.variants.configure(values=[f'V-{e["variant"]:02X}' for e in monster['variants']]);self.variants.current(0)
        self.name.set(self.workspace.data.get('monster_names',{}).get(monster['code'],''));self.spawn()

    def select_entry(self,entry,spawn=True):
        monster=next((m for m in self.monsters if m['type']==entry['type']),None)
        if not monster:return False
        variants=monster['variants'];index=next((i for i,v in enumerate(variants) if v.get('variant',0)==entry.get('variant',0)),0)
        self.entry=dict(variants[index],_chosen=True);self.show_bosses.set(self.show_bosses.get() or monster['boss']);self.refresh_monsters()
        if self.picker.exists(monster['code']):
            self.picker.selection_set(monster['code']);self.picker.see(monster['code'])
        self.variants.configure(values=[f'V-{v.get("variant",0):02X}' for v in variants]);self.variants.current(index)
        self.name.set(self.workspace.data.get('monster_names',{}).get(monster['code'],''))
        if spawn:self.spawn()
        else:
            self.update_details()
            if self.on_selected:self.on_selected(self.entry)
        return True

    def set_active(self,value):
        self.active=bool(value);self.send('pause',value=self.paused.get() or not self.active)
    def change_variant(self,*_):
        monster=next(m for m in self.monsters if m['type']==self.entry['type'])
        self.entry=dict(monster['variants'][self.variants.current()],_chosen=True);self.spawn()
    def change_mode(self,*_):
        self.still.set(False);self.paused.set(False);self.snapshot={'actors':[]}
        self.send('quest',value=1 if self.preview_mode.get()=='New Game+' else 0)
    def save_name(self):
        self.workspace.data.setdefault('monster_names',{})[code(self.entry['type'])]=self.name.get().strip()
        self.workspace.save();self.refresh_monsters();self.update_details()
        self.status.set('Anzeigename gespeichert. Der stabile Monster-Code bleibt gleich.')
        if self.on_name_changed:self.on_name_changed(dict(self.workspace.data['monster_names']))

    def spawn(self):
        if not self.catalog:return
        self.still.set(False);self.paused.set(False);self.active_action='Natürlich';self.snapshot={'actors':[]}
        self.invalidate()
        if not self.worker.is_alive() and not self.closing:
            rom,build,library=self.runtime_args;self.commands=queue.Queue();self.events=queue.Queue(maxsize=8)
            self.worker=Worker(self.commands,self.events,rom,build,arena=True,library=library,initial_entry=self.entry);self.worker.start()
        else:self.send('spawn',entry=self.entry)
        self.update_details()
        if not self.active:self.send('pause',value=True)
        if self.on_selected:self.on_selected(self.entry)

    def run_action(self,action):
        if not actions(self.entry).get(action):return
        self.still.set(False);self.paused.set(False);self.active_action=action
        self.send('action',value=action)
    def single_step(self):
        self.still.set(False);self.paused.set(True);self.send('pause',value=True);self.send('step')
    def still_changed(self):
        self.paused.set(self.still.get());self.send('pause',value=self.paused.get())
    def tab_changed(self,*_):
        group=GROUPS[self.tabs.index('current')];tree=self.trees[group]
        if tree.selection():self.select_pose(tree)
        elif tree.get_children():tree.selection_set(tree.get_children()[0]);self.select_pose(tree)
        else:self.selected_id=None;self.file.set('Für diese Aktion ist noch keine Pose zugeordnet.')
    def select_pose(self,tree):
        selected=tree.selection()
        if not selected:return
        self.selected_id=selected[0];frame=self.workspace.frames[self.selected_id]
        self.file.set(str(self.workspace.folder/'artwork'/frame['image']))
    def open_png(self):
        if self.selected_id:os.startfile(self.workspace.folder/'artwork'/self.workspace.frames[self.selected_id]['image'])
    def replace(self):
        if not self.selected_id:return
        path=filedialog.askopenfilename(parent=self.root,title='PNG ersetzen',filetypes=[('PNG','*.png')])
        if path:
            try:
                self.workspace.replace(self.selected_id,path)
                self.hd_counts=self._scan_hd_actors();self.refresh_monsters();self.update_details()
                self.status.set('PNG übernommen. Das HD-Redesign wird live aktualisiert.')
            except (ValueError,OSError) as error:messagebox.showerror('PNG ersetzen',str(error),parent=self.root)
    def export(self):
        path=filedialog.asksaveasfilename(parent=self.root,title='Monster-PNGs exportieren',initialfile=code(self.entry['type'])+'.zip',defaultextension='.zip',filetypes=[('ZIP','*.zip')])
        if path:
            try:
                count=export_monster(self.workspace,self.entry,path,self.live_ids.get(profile_key(self.entry),()),self.graphics_variants.get())
                self.status.set(f'{count} PNGs mit Aktionszuordnung exportiert: {path}')
            except (ValueError,OSError) as error:messagebox.showerror('PNG-Set',str(error),parent=self.root)
    def build_pack(self):
        destination=ROOT/'artwork-local/enemies'/('monster-'+time.strftime('%Y%m%d-%H%M%S'))
        try:
            count=self.workspace.build_pack(destination);self.status.set(f'{count} Zuordnungen gepackt: {destination}');os.startfile(destination)
        except (ValueError,OSError) as error:messagebox.showinfo('HD-Paket',str(error),parent=self.root)

    def update_details(self):
        c=code(self.entry['type'])
        custom_name=self.workspace.data.get('monster_names',{}).get(c,'')
        self.monster_title.set(f'{custom_name}  ({c})' if custom_name else c)
        hd_n=self.hd_counts.get(self.entry['type'],0)
        if hd_n>0:
            self.hd_badge.set(f'✦ HD AKTIV ({hd_n} Posen)')
            if self.hd_badge_lbl:self.hd_badge_lbl.configure(style='BadgeHD.TLabel')
        else:
            self.hd_badge.set('Original 1× (noch kein HD)')
            if self.hd_badge_lbl:self.hd_badge_lbl.configure(style='BadgeSD.TLabel')

        live=self.snapshot.get('live_stats',{});stats=combat_stats(self.rom,self.entry,live)
        value=lambda key:stats[key] if stats[key] is not None else '—'
        normal=stats['profiles']['normal'];plus=stats['profiles']['new_game_plus']
        fmt=lambda number:'—' if number is None else str(number)
        delta=plus['hp']-normal['hp'] if plus['hp'] is not None and normal['hp'] is not None else None
        self.comparison.item('hp',values=('Gesundheit',fmt(normal['hp']),fmt(plus['hp'])+(f' (+{delta})' if delta else '')))
        self.comparison.item('contact',values=('Kontaktschaden',fmt(normal['contact_damage']),fmt(plus['contact_damage'])))
        live_mode='New Game+' if stats['live_quest'] else 'Normal' if stats['live_quest']==0 else '—'
        self.stats.set(f'{c} · V-{self.entry.get("variant",0):02X}\n\n'
            f'Live-Szene: {live_mode}\nGesundheit aktuell: {value("current_hp")}\nGrundwert: {value("base_hp")}\n'
            f'Raumzuschlag Normal / NG+: {normal["room_bonus"]} / {plus["room_bonus"]+plus["quest_bonus"]}\n\n'
            f'Trefferbox: {value("hitbox_width")} × {value("hitbox_height")} px\nZustand: {value("state")}\n'
            f'Position: {value("x")} / {value("y")}\nMotor vX / vY: '+
            (f'{stats["speed_x"]:.2f} / {stats["speed_y"]:.2f}' if stats['speed_x'] is not None else '—'))
        note_str=ai_notes(self.entry)
        if note_str!=self.notes.get():
            self._set_notes_text(note_str)
        self.context.set(self.snapshot['context_error'] if self.snapshot.get('context_error') else
            'Boss im neutralen Testraum: Original-KI & Grafiken ohne Herkunftslevel, feste Kamera.' if self.entry.get('boss') else
            'Neutraler Testraum mit flachem Boden. „Ziel links / rechts“ steuert das Spielerziel für die Original-KI.')
        supported=actions(self.entry)
        for group,button in self.buttons.items():
            action={'Gehen / Bewegen':'Gehen'}.get(group,group)
            button.configure(state='normal' if supported.get(action) and not self.snapshot.get('context_error') else 'disabled')

    def refresh_poses(self):
        groups=frame_groups(self.entry,self.workspace,self.live_ids.get(profile_key(self.entry),()))
        filtered=visible_frames(groups,self.parts.get(),self.graphics_variants.get())
        signature=tuple((group,tuple(f['id'] for f in frames)) for group,frames in filtered.items())
        if signature==self.signature:return
        self.signature=signature;supported=actions(self.entry)
        for group,tree in self.trees.items():
            selection=tree.selection();tree.delete(*tree.get_children());rows=filtered[group]
            for frame in rows:
                role='Körper' if frame['actor_type']==self.entry.get('main_type',self.entry['type']) else 'Effekt' if group=='Sterben' else f'Geschoss / Teil {frame["actor_type"]:04X}'
                if frame['component']:role+=' · Einzelteil'
                label=f'P-{frame["pose"]:04X}'
                if frame['component']:label+=' / T-'+frame['id'].rsplit('__teil-',1)[1].zfill(2)
                tree.insert('','end',iid=frame['id'],text=label,values=(role,'ROM-Vorlage' if frame.get('source_kind')=='rom_pose' else 'Originalaufnahme'))
            action={'Gehen / Bewegen':'Gehen'}.get(group,group)
            text=f'{len(rows)} PNGs'
            if group=='Springen' and self.entry['type'] in (0x12,0x31,0x56):text+=' · benutzt die Gehbilder'
            elif group=='Springen' and self.entry['type'] in (0x11,0x69):text+=' · kein eigener KI-Sprung'
            elif group=='Angriff' and self.entry['type'] in (0x11,0x69):text+=' · Kontakt, keine eigene Angriffspose'
            elif group!='Noch zuordnen' and not supported.get(action):text+=' · Aktion noch ungeprüft'
            elif not rows:text+=' · beim Abspielen aufnehmen'
            self.hints[group].set(text)
            if rows:tree.selection_set(selection[0] if selection and tree.exists(selection[0]) else rows[0]['id'])
        self.tab_changed()

    def tick(self):
        if self.closing:return
        try:
            while True:
                event=self.events.get_nowait()
                if 'catalog' in event and not self.catalog:
                    self.catalog=event['catalog'];self.monsters=definitions(self.catalog,self.rom);self.select_entry(self.entry,spawn=False)
                key=event.get('profile_key')
                if key:self.live_ids.setdefault(key,set()).update(event.get('profile_frame_ids',()))
                self.allowed.update(event.get('allowed_ids',()))
                if 'references' in event:self.references=Path(event['references'])
                if 'snapshot' in event and key==profile_key(self.entry):
                    self.snapshot=event['snapshot'];self.active_action=event.get('active_action','Natürlich')
                    if self.snapshot.get('context_error'):self.paused.set(True)
                    if self.active_action=='Sterben' and self.snapshot.get('live_stats',{}).get('hp')==0:
                        records=self.workspace.data.setdefault('monster_actions',{}).setdefault(key,{}).setdefault('Sterben',[])
                        for actor in self.snapshot['actors']:
                            identifiers=[actor['id']]+[p['id'] for p in actor['parts']]
                            for identifier in identifiers:
                                if identifier not in records:records.append(identifier);self.dirty=True;self.invalidate()
                self.status.set(event.get('fatal',event.get('error',event.get('status',self.status.get()))))
        except queue.Empty:pass
        now=time.monotonic()
        if self.active and self.references and now-self.last_ingest>.5:
            self.workspace.ingest(self.references,self.allowed);self.last_ingest=now
        if self.dirty and now-self.last_save>2:self.workspace.save();self.dirty=False;self.last_save=now
        if not self.active:
            self.tick_id=self.root.after(200,self.tick);return
        self.update_details();self.refresh_poses();self.photos=[]
        zoom_scale=ZOOM_OPTIONS.get(self.zoom_label.get(),2.5)
        backdrop=BACKDROP_OPTIONS.get(self.backdrop_label.get(),'gothic')
        for i,canvas in enumerate(self.canvases):
            size=max(2,canvas.winfo_width()),max(2,canvas.winfo_height())
            if self.still.get() and self.selected_id:
                picture=pose_preview(self.workspace,self.selected_id,bool(i),size,backdrop=backdrop)
            else:
                picture=preview(self.snapshot,self.workspace,bool(i),size,zoom_scale=zoom_scale,backdrop=backdrop)
            photo=ImageTk.PhotoImage(picture,master=self.root);self.photos.append(photo);canvas.delete('all');canvas.create_image(0,0,anchor='nw',image=photo)
        if self.workspace.last_error:self.status.set(self.workspace.last_error)
        self.tick_id=self.root.after(50,self.tick)

    def close(self):
        if self.closing:return True
        try:self.workspace.save()
        except OSError as error:messagebox.showerror('Monster-Werkstatt speichern',str(error),parent=self.root);return False
        self.closing=True
        if self.tick_id:self.root.after_cancel(self.tick_id);self.tick_id=None
        self.worker.stopping=True;self.send('stop')
        def finish():
            if self.worker.is_alive():self.root.after(50,finish)
            else:
                self.closed=True
                if not self.embedded:self.root.destroy()
        finish()
        return True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',type=Path);parser.add_argument('--build',type=Path)
    parser.add_argument('--workspace',type=Path,default=DEFAULT_WORKSPACE);parser.add_argument('--library',type=Path,default=DEFAULT_LIBRARY)
    args=parser.parse_args()
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError,OSError):pass
    root=tk.Tk();MonsterWorkshop(root,args.rom,args.build,args.workspace,args.library);root.mainloop()


if __name__=='__main__':main()
