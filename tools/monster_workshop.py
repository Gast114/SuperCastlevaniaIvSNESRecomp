"""Monster-first native test arena, action library and live artwork editor."""
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

from PIL import ImageTk
from enemy_workshop import Worker, preview, pose_preview, DEFAULT_WORKSPACE
from enemy_workshop_assets import Workspace
from enemy_workshop_library import DEFAULT_LIBRARY, profile_key
from enemy_workshop_native import ROOT
from monster_model import GROUPS, actions, ai_notes, code, combat_stats, definitions, frame_groups, visible_frames


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
    def __init__(self,root,rom=None,build=None,workspace=DEFAULT_WORKSPACE,library=DEFAULT_LIBRARY):
        self.root=root;self.workspace=Workspace(workspace)
        if library and (Path(library)/'library.json').is_file():self.workspace.load_library(library)
        self.rom=Path(rom or ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
        self.commands=queue.Queue();self.events=queue.Queue(maxsize=8)
        self.catalog=[];self.monsters=[];self.entry={'type':18,'variant':0}
        self.snapshot={'actors':[]};self.references=None;self.allowed=set();self.live_ids={}
        self.selected_id=None;self.signature=None;self.photos=[];self.closing=False
        self.last_ingest=0.;self.last_save=0.;self.dirty=False;self.active_action='Natürlich'
        self.name=tk.StringVar();self.variant=tk.StringVar();self.parts=tk.BooleanVar(value=False)
        self.paused=tk.BooleanVar(value=False);self.still=tk.BooleanVar(value=False)
        self.speed=tk.StringVar(value='100%');self.show_bosses=tk.BooleanVar(value=False)
        self.graphics_variants=tk.BooleanVar(value=False)
        self.preview_mode=tk.StringVar(value='Normal')
        self.status=tk.StringVar(value='Eigene Original-Laufzeit startet …')
        self.context=tk.StringVar(value='Monster per Code wählen. Namen kannst du selbst vergeben.')
        self.stats=tk.StringVar();self.notes=tk.StringVar();self.file=tk.StringVar()
        root.title('Monster-Werkstatt · Super Castlevania IV')
        scale=max(1.,float(root.tk.call('tk','scaling'))/(96/72),min(root.winfo_screenwidth()/1920,root.winfo_screenheight()/1080))
        root.tk.call('tk','scaling',96/72*scale)
        root.geometry(f'{min(round(1540*scale),root.winfo_screenwidth()-60)}x{min(round(980*scale),root.winfo_screenheight()-90)}')
        root.minsize(min(round(1060*scale),root.winfo_screenwidth()-80),min(round(700*scale),root.winfo_screenheight()-100))
        style=ttk.Style();style.configure('.',font=('Segoe UI',11));style.configure('Treeview',rowheight=round(30*scale))
        outer=ttk.Frame(root,padding=14);outer.pack(fill='both',expand=True)
        ttk.Label(outer,text='Monster-Werkstatt',font=('Segoe UI',22,'bold')).pack(anchor='w')
        ttk.Label(outer,text='Monster auswählen · Aktionen prüfen · Original und Redesign live vergleichen').pack(anchor='w',pady=(0,10))
        split=ttk.Panedwindow(outer,orient='horizontal');split.pack(fill='both',expand=True)
        left=ttk.Frame(split,width=round(220*scale));center=ttk.Frame(split);right=ttk.Frame(split,width=round(300*scale))
        split.add(left,weight=0);split.add(center,weight=1);split.add(right,weight=0)
        ttk.Label(left,text='Monster-Codes').pack(anchor='w')
        self.picker=ttk.Treeview(left,show='tree',selectmode='browse',height=15)
        self.picker.column('#0',width=round(215*scale),stretch=True)
        scrollbar=ttk.Scrollbar(left,command=self.picker.yview);self.picker.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y');self.picker.pack(fill='both',expand=True)
        self.picker.bind('<<TreeviewSelect>>',self.choose)
        ttk.Checkbutton(left,text='Bosse / Originalszene',variable=self.show_bosses,command=self.refresh_monsters).pack(anchor='w',pady=6)
        ttk.Label(left,text='Dein Name').pack(anchor='w');ttk.Entry(left,textvariable=self.name).pack(fill='x')
        ttk.Button(left,text='Namen speichern',command=self.save_name).pack(fill='x',pady=5)
        ttk.Label(left,text='Variante').pack(anchor='w')
        self.variants=ttk.Combobox(left,textvariable=self.variant,state='readonly',width=18)
        self.variants.pack(fill='x');self.variants.bind('<<ComboboxSelected>>',self.change_variant)
        ttk.Button(left,text='Spawnen / neu starten',command=self.spawn).pack(fill='x',pady=8)
        views=ttk.Frame(center);views.pack(fill='both',expand=True);self.canvases=[]
        for title in ('Original','Dein Redesign · live'):
            box=ttk.LabelFrame(views,text=title,padding=4);box.pack(side='left',fill='both',expand=True,padx=3)
            canvas=tk.Canvas(box,background='#19212c',highlightthickness=0,width=256,height=224)
            canvas.pack(fill='both',expand=True);self.canvases.append(canvas)
        controls=ttk.Frame(center);controls.pack(fill='x',pady=8)
        ttk.Checkbutton(controls,text='Pause',variable=self.paused,command=lambda:self.send('pause',value=self.paused.get())).pack(side='left')
        ttk.Button(controls,text='Ein Feld',command=self.single_step).pack(side='left',padx=4)
        box=ttk.Combobox(controls,textvariable=self.speed,values=['25%','50%','100%'],state='readonly',width=6)
        box.pack(side='left');box.bind('<<ComboboxSelected>>',lambda _:self.send('speed',value=float(self.speed.get().strip('%'))/100))
        ttk.Button(controls,text='Ziel links',command=lambda:self.send('direction',value='Links')).pack(side='left',padx=4)
        ttk.Button(controls,text='Ziel rechts',command=lambda:self.send('direction',value='Rechts')).pack(side='left')
        ttk.Button(controls,text='Natürlich',command=lambda:self.run_action('Natürlich')).pack(side='left',padx=4)
        self.tabs=ttk.Notebook(center);self.tabs.pack(fill='both',expand=True)
        self.trees={};self.buttons={};self.hints={}
        for group in GROUPS:
            panel=ttk.Frame(self.tabs,padding=8);self.tabs.add(panel,text=group)
            bar=ttk.Frame(panel);bar.pack(fill='x')
            action={'Gehen / Bewegen':'Gehen'}.get(group,group)
            button=ttk.Button(bar,text='Aktion abspielen',command=lambda a=action:self.run_action(a))
            if group!='Noch zuordnen':button.pack(side='left');self.buttons[group]=button
            hint=tk.StringVar();self.hints[group]=hint
            ttk.Label(bar,textvariable=hint,wraplength=round(490*scale)).pack(side='left',padx=8)
            tree=ttk.Treeview(panel,columns=('role','source'),show='tree headings',height=5,selectmode='browse')
            tree.heading('#0',text='Posen-Code');tree.column('#0',width=150)
            tree.heading('role',text='Bestandteil');tree.column('role',width=150)
            tree.heading('source',text='Zuordnung');tree.column('source',width=170)
            scroll=ttk.Scrollbar(panel,command=tree.yview);tree.configure(yscrollcommand=scroll.set)
            scroll.pack(side='right',fill='y');tree.pack(fill='both',expand=True)
            tree.bind('<<TreeviewSelect>>',lambda event,t=tree:self.select_pose(t));self.trees[group]=tree
        self.tabs.bind('<<NotebookTabChanged>>',self.tab_changed)
        edit=ttk.Frame(center);edit.pack(fill='x',pady=6)
        ttk.Checkbutton(edit,text='Einzelteile',variable=self.parts,command=self.invalidate).pack(side='left')
        ttk.Checkbutton(edit,text='Grafikvarianten',variable=self.graphics_variants,command=self.invalidate).pack(side='left')
        ttk.Checkbutton(edit,text='PNG einzeln ansehen',variable=self.still,command=self.still_changed).pack(side='left',padx=5)
        ttk.Button(edit,text='PNG öffnen',command=self.open_png).pack(side='left')
        ttk.Button(edit,text='PNG ersetzen',command=self.replace).pack(side='left',padx=5)
        ttk.Label(center,textvariable=self.file,wraplength=round(730*scale)).pack(anchor='w')
        details=ttk.Notebook(right);details.pack(fill='both',expand=True,pady=(0,8))
        stats_panel=ttk.Frame(details,padding=8);ai_panel=ttk.Frame(details,padding=8)
        details.add(stats_panel,text='Werte');details.add(ai_panel,text='KI / Hinweise')
        ttk.Label(stats_panel,text='Werte aus dem Original',font=('Segoe UI',13,'bold')).pack(anchor='w',pady=8)
        self.comparison=ttk.Treeview(stats_panel,columns=('stat','normal','ng'),show='headings',height=2,selectmode='none')
        for key,label,width in (('stat','Startwert',136),('normal','Normal',72),('ng','New Game+',94)):
            self.comparison.heading(key,text=label);self.comparison.column(key,width=round(width*scale),stretch=True)
        self.comparison.insert('','end',iid='hp',values=('Gesundheit','—','—'))
        self.comparison.insert('','end',iid='contact',values=('Kontaktschaden','—','—'))
        self.comparison.pack(fill='x',pady=(0,8))
        mode_row=ttk.Frame(stats_panel);mode_row.pack(fill='x',pady=(0,8))
        ttk.Label(mode_row,text='Vorschau:').pack(side='left',padx=(0,5))
        mode_box=ttk.Combobox(mode_row,textvariable=self.preview_mode,values=['Normal','New Game+'],state='readonly',width=14)
        mode_box.pack(side='left');mode_box.bind('<<ComboboxSelected>>',self.change_mode)
        ttk.Label(stats_panel,textvariable=self.stats,justify='left').pack(anchor='w')
        ttk.Label(ai_panel,text='KI / Verhalten',font=('Segoe UI',13,'bold')).pack(anchor='w',pady=(8,8))
        ttk.Label(ai_panel,textvariable=self.notes,wraplength=round(295*scale),justify='left').pack(anchor='w')
        ttk.Label(ai_panel,textvariable=self.context,wraplength=round(295*scale),justify='left').pack(anchor='w',pady=14)
        ttk.Button(right,text='Dieses Monster als PNG-Set',command=self.export).pack(fill='x',pady=4)
        ttk.Button(right,text='HD-Paket erstellen',command=self.build_pack).pack(fill='x',pady=4)
        ttk.Button(right,text='Arbeitsordner öffnen',command=lambda:os.startfile(self.workspace.folder)).pack(fill='x',pady=4)
        ttk.Label(outer,textvariable=self.status,wraplength=round(1400*scale)).pack(anchor='w',pady=(8,0))
        self.worker=Worker(self.commands,self.events,rom,build,arena=True);self.worker.start()
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(50,self.tick)

    def send(self,kind,**values):self.commands.put(dict(kind=kind,**values))
    def invalidate(self):self.signature=None
    def refresh_monsters(self):
        selected=self.picker.selection();current=selected[0] if selected else code(self.entry['type'])
        self.picker.delete(*self.picker.get_children())
        names=self.workspace.data.get('monster_names',{})
        for monster in self.monsters:
            if monster['boss'] and not self.show_bosses.get():continue
            c=monster['code'];name=names.get(c,'')
            self.picker.insert('','end',iid=c,text=c+(' · '+name if name else ''))
        if self.picker.exists(current):self.picker.selection_set(current)
    def choose(self,*_):
        selection=self.picker.selection()
        if not selection:return
        monster=next(m for m in self.monsters if m['code']==selection[0])
        if self.entry.get('_chosen') and self.entry['type']==monster['type']:return
        self.entry=dict(monster['variants'][0],_chosen=True)
        self.variants.configure(values=[f'V-{e["variant"]:02X}' for e in monster['variants']]);self.variants.current(0)
        self.name.set(self.workspace.data.get('monster_names',{}).get(monster['code'],''));self.spawn()
    def change_variant(self,*_):
        monster=next(m for m in self.monsters if m['type']==self.entry['type'])
        self.entry=dict(monster['variants'][self.variants.current()],_chosen=True);self.spawn()
    def change_mode(self,*_):
        self.still.set(False);self.paused.set(False);self.snapshot={'actors':[]}
        self.send('quest',value=1 if self.preview_mode.get()=='New Game+' else 0)
    def save_name(self):
        self.workspace.data.setdefault('monster_names',{})[code(self.entry['type'])]=self.name.get().strip()
        self.workspace.save();self.refresh_monsters();self.status.set('Dein Name ist gespeichert. Der Monster-Code bleibt gleich.')
    def spawn(self):
        if not self.catalog:return
        self.still.set(False);self.paused.set(False);self.active_action='Natürlich';self.snapshot={'actors':[]}
        self.invalidate();self.send('spawn',entry=self.entry);self.update_details()
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
            try:self.workspace.replace(self.selected_id,path);self.status.set('PNG übernommen. Das Redesign wird live aktualisiert.')
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
        live=self.snapshot.get('live_stats',{});stats=combat_stats(self.rom,self.entry,live)
        value=lambda key:stats[key] if stats[key] is not None else '—'
        normal=stats['profiles']['normal'];plus=stats['profiles']['new_game_plus']
        fmt=lambda number:'—' if number is None else str(number)
        delta=plus['hp']-normal['hp'] if plus['hp'] is not None and normal['hp'] is not None else None
        self.comparison.item('hp',values=('Gesundheit',fmt(normal['hp']),fmt(plus['hp'])+(f' (+{delta})' if delta else '')))
        self.comparison.item('contact',values=('Kontaktschaden',fmt(normal['contact_damage']),fmt(plus['contact_damage'])))
        live_mode='New Game+' if stats['live_quest'] else 'Normal' if stats['live_quest']==0 else '—'
        self.stats.set(f'{code(self.entry["type"])} · V-{self.entry.get("variant",0):02X}\n\n'
            f'Live-Szene: {live_mode}\nGesundheit aktuell: {value("current_hp")}\nGrundwert: {value("base_hp")}\n'
            f'Raumzuschlag Normal / NG+: {normal["room_bonus"]} / {plus["room_bonus"]+plus["quest_bonus"]}\n'
            'HP: interne Schadenseinheiten\nKontakt: Spieler-Lebenspunkte\n\n'
            f'Trefferbox: {value("hitbox_width")} × {value("hitbox_height")} px\nZustand: {value("state")}\n'
            f'Position: {value("x")} / {value("y")}\nMotor vX / vY: '+
            (f'{stats["speed_x"]:.2f} / {stats["speed_y"]:.2f}' if stats['speed_x'] is not None else '—'))
        self.notes.set(ai_notes(self.entry))
        self.context.set(self.snapshot['context_error'] if self.snapshot.get('context_error') else
            'Boss: feste Testkamera und geschütztes Spielerziel im ursprünglichen Kollisionsraum.' if self.entry.get('boss') else
            'Neutrale Arena: flacher Boden und Seitenwände. Ziel links/rechts versetzt das Spielerziel für die Original-KI.\n\n'
            'Grau deaktivierte Aktionen sind noch ungeprüft. Springen und Angriff fehlen bei manchen Monstern tatsächlich; eine leere Gruppe behauptet das nicht.')
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
                    self.catalog=event['catalog'];self.monsters=definitions(self.catalog,self.rom);self.refresh_monsters()
                key=event.get('profile_key')
                if key:self.live_ids.setdefault(key,set()).update(event.get('profile_frame_ids',()))
                self.allowed.update(event.get('allowed_ids',()))
                if 'references' in event:self.references=Path(event['references'])
                if 'snapshot' in event and key==profile_key(self.entry):
                    self.snapshot=event['snapshot'];self.active_action=event.get('active_action','Natürlich')
                    if self.snapshot.get('context_error'):self.paused.set(True)
                    # Persist only actual death observations, excluding unchanged body poses.
                    if self.active_action=='Sterben' and self.snapshot.get('live_stats',{}).get('hp')==0:
                        records=self.workspace.data.setdefault('monster_actions',{}).setdefault(key,{}).setdefault('Sterben',[])
                        for actor in self.snapshot['actors']:
                            identifiers=[actor['id']]+[p['id'] for p in actor['parts']]
                            for identifier in identifiers:
                                if identifier not in records:records.append(identifier);self.dirty=True;self.invalidate()
                self.status.set(event.get('fatal',event.get('error',event.get('status',self.status.get()))))
        except queue.Empty:pass
        now=time.monotonic()
        if self.references and now-self.last_ingest>.5:
            self.workspace.ingest(self.references,self.allowed);self.last_ingest=now
        if self.dirty and now-self.last_save>2:self.workspace.save();self.dirty=False;self.last_save=now
        self.update_details();self.refresh_poses();self.photos=[]
        for i,canvas in enumerate(self.canvases):
            size=max(2,canvas.winfo_width()),max(2,canvas.winfo_height())
            picture=pose_preview(self.workspace,self.selected_id,bool(i),size) if self.still.get() and self.selected_id else preview(self.snapshot,self.workspace,bool(i),size)
            photo=ImageTk.PhotoImage(picture);self.photos.append(photo);canvas.delete('all');canvas.create_image(0,0,anchor='nw',image=photo)
        if self.workspace.last_error:self.status.set(self.workspace.last_error)
        self.root.after(50,self.tick)
    def close(self):
        self.closing=True;self.workspace.save();self.worker.stopping=True;self.send('stop')
        def finish():
            if self.worker.is_alive():self.root.after(50,finish)
            else:self.root.destroy()
        finish()


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
