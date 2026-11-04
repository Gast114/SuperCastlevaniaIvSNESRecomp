"""One application owns the level workspace and the embedded monster workshop."""
from tkinter import ttk,messagebox
from enemy_workshop import DEFAULT_WORKSPACE
from enemy_workshop_library import DEFAULT_LIBRARY
from enemy_workshop_assets import Workspace
from monster_workshop import MonsterWorkshop


class MonsterPanel:
    def __init__(self,editor,workspace=DEFAULT_WORKSPACE,library=DEFAULT_LIBRARY):
        self.editor=editor;self.workspace_path=workspace;self.library=library;self.workshop=None
        self.visible=False;self.loading=False;self.prepared=None;self.pending=None;self.target=None
        self.placeholder=ttk.Frame(editor.monster_page,padding=24);self.placeholder.pack(fill='both',expand=True)
        ttk.Label(self.placeholder,text='Monster & Animationen',style='Heading.TLabel').pack(anchor='w')
        self.loading_label=ttk.Label(self.placeholder,text='Die Werkstatt startet, sobald du diesen Bereich öffnest.');self.loading_label.pack(anchor='w',pady=12)
        self.retry_button=ttk.Button(self.placeholder,text='Erneut laden',command=self.show)

    def source(self,entry=None):
        editor=self.editor;actor=editor.object() if editor.selected_object and editor.selected_object[0]=='actor' else None
        if actor and not any(m['type']==actor['type'] for m in editor.definitions):actor=None
        if entry is None:entry=actor or editor.library_entry('Monster') or editor.monster_template or {'type':18,'variant':0}
        self.pending=dict(entry)
        self.target=(dict(project=editor.project,room=editor.room_id,actor=actor['id'],original=editor.original_number if editor.original_view else None)
            if actor and actor['type']==entry['type'] else None)
        if self.workshop:
            if (self.workshop.entry['type'],self.workshop.entry.get('variant',0))!=(entry['type'],entry.get('variant',0)):self.workshop.select_entry(entry)
            self.context(self.workshop.entry)

    def show(self):
        self.visible=True;self.editor.stop_level_test()
        if self.workshop:self.workshop.set_active(True);return
        if self.prepared is not None:self.mount(self.prepared);return
        if self.loading:return
        self.loading=True;self.retry_button.pack_forget();self.loading_label.configure(text='PNG-Bibliothek und vorhandene Redesigns werden geladen …')
        def prepare():
            try:
                workspace=Workspace(self.workspace_path)
                if self.library:workspace.load_library(self.library)
                return 'studio_workspace',workspace
            except Exception as error:return 'studio_error',str(error)
        self.editor.background(prepare)

    def failed(self,error):
        self.loading=False;self.loading_label.configure(text='Die Monsterbibliothek konnte nicht geladen werden.\n'+error);self.retry_button.pack(anchor='w')

    def ready(self,workspace):
        self.loading=False;self.prepared=workspace
        if self.visible:self.mount(workspace)

    def mount(self,workspace):
        self.placeholder.pack_forget();editor=self.editor
        catalog=[dict(v) for m in editor.definitions for v in m['variants']]
        self.workshop=MonsterWorkshop(editor.monster_page,workspace=workspace,library=None,embedded=True,catalog=catalog,
            initial_entry=self.canonical(self.pending or {'type':18,'variant':0}),on_place=self.place,on_values=self.values,
            on_name_changed=self.names,on_selected=self.context)
        self.workshop.set_active(self.visible);self.context(self.workshop.entry)

    def canonical(self,entry):
        rows=[v for m in self.editor.definitions if m['type']==entry['type'] for v in m['variants']]
        return next((v for v in rows if v.get('variant',0)==entry.get('variant',0)),rows[0] if rows else {'type':18,'variant':0})

    def linked_actor(self,entry):
        target=self.target;editor=self.editor
        if not target or target['project'] is not editor.project:return None
        if target['original'] is not None:
            if not editor.original_view or editor.original_number!=target['original'] or editor.original_room is None:return None
            room=editor.original_room
        else:room=next((r for r in editor.project.data['rooms'] if r['id']==target['room']),None)
        actor=next((a for a in room['actors'] if a['id']==target['actor'] and a['type']==entry['type']),None) if room else None
        return (room,actor) if actor else None

    def context(self,entry):
        editor=self.editor;identifier=f'M-{entry["type"]:04X}'
        if editor.monsters.exists(identifier):editor.monsters.selection_set(identifier);editor.monster_template=self.canonical(entry)
        if not self.workshop:return
        linked=self.linked_actor(entry)
        self.workshop.level_context.set(f'{identifier} · Verknüpft mit „{linked[0]["name"]}“\nAnimationen und HD-Bilder bearbeiten; Levelwerte über die Schaltfläche ändern.' if linked else
            f'{identifier} · Neutraler Testraum\nÜber „Im Level hinzufügen“ direkt in den geöffneten Raum setzen.')
        self.workshop.values_button.configure(state='normal' if linked else 'disabled')

    def names(self,names):
        self.editor.library_names=dict(names);self.editor.filter_monsters();self.editor.schedule()

    def place(self,entry):
        editor=self.editor;row=self.canonical(entry)
        if row['type']!=entry['type']:editor.status.set('Dieser Code ist noch kein platzierbarer Gegner.');return
        editor.workspaces.select(editor.level_page);self.hide();editor.root.update_idletasks();editor.place_actor(row,*self.center())

    def center(self):
        editor=self.editor;canvas=editor.canvas;room=editor.current();zoom=editor.zoom.get()
        return (round((max(0,canvas.canvasx(0)/zoom)+min(room['width']*8,canvas.canvasx(canvas.winfo_width())/zoom))/2),
                round((max(0,canvas.canvasy(0)/zoom)+min(room['height']*8,canvas.canvasy(canvas.winfo_height())/zoom))/2))

    def values(self,entry):
        linked=self.linked_actor(entry)
        if not linked:return
        editor=self.editor;room,actor=linked
        if self.target['original'] is not None:
            if not editor.ensure_editable():return
            self.target=dict(project=editor.project,room=editor.room_id,actor=actor['id'],original=None)
        else:
            editor.original_view=False;editor.room_id=room['id'];editor.room_tabs.select(editor.project_tab);editor.refresh_rooms()
        editor.selected_object=('actor',actor['id']);editor.object_fields();editor.actor_details();self.context(entry)

    def hide(self):
        self.visible=False
        if self.workshop:self.workshop.set_active(False)
        self.editor.schedule()

    def save(self):
        if self.workshop:
            try:self.workshop.workspace.save();self.workshop.status.set('Monsterbilder und Namen gespeichert.')
            except OSError as error:messagebox.showerror('Monster-Werkstatt speichern',str(error),parent=self.editor.root)

    def pause(self):
        if self.workshop:self.workshop.paused.set(True);self.workshop.send('pause',value=True)

    def close(self):return self.workshop.close() if self.workshop else True
    def stopped(self):return self.workshop is None or self.workshop.closed
