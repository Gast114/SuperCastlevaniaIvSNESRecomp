"""Local Photoshop → character/enemy pack review and explicit installation."""
from datetime import datetime
from pathlib import Path
import html
import json
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from import_character_hd import import_poses, make_workspace
from install_character_pack import install_pack
import enemy_hd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
READY_ENEMY_WORKSPACE = ROOT.parent/'Assets (ausgeschnitten)'/'Gegner'/'01_Skelette'


def enemy_preview(target):
    data = json.loads((target/'enemies.json').read_text(encoding='utf-8'))
    names = sorted({frame['image'] for frame in data['frames']})
    cards = []
    for name in names:
        with Image.open(target/name) as image:
            width, height = image.size
        count = sum(frame['image'] == name for frame in data['frames'])
        cards.append(f'<article><img src="{html.escape(quote(name), quote=True)}" alt="Gegnerbild">'
                     f'<h2>{html.escape(Path(name).stem.replace("_", " "))}</h2>'
                     f'<p>{width} × {height} PNG-Pixel · {count} automatisch zugeordnete Spielzustände</p></article>')
    (target/'preview.html').write_text('<!doctype html><meta charset="utf-8"><title>Gegner-HD prüfen</title>'
        '<style>body{font:17px system-ui;background:#20232a;color:#eee;padding:2rem}main{display:flex;gap:24px;flex-wrap:wrap}'
        'article{padding:20px;background:#30343d}img{width:280px;height:280px;object-fit:contain}</style>'
        '<h1>Gegner-Paket vorbereitet</h1><p>Die PNGs wurden unverändert übernommen. '
        'Position, Gegenrichtung und Spielzustände werden automatisch zugeordnet.</p>'
        '<p>Nach Sichtprüfung im Importfenster „Paket in beide Spielversionen einbauen“ anklicken.</p>'
        '<main>'+''.join(cards)+'</main>', encoding='utf-8')


def main():
    root = tk.Tk()
    root.title('HD-Import · Super Castlevania IV')
    root.geometry('790x665')
    root.minsize(730, 640)
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Deine PNGs ins Spiel übernehmen', font=('Segoe UI', 17, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Arbeitsauflösung frei wählen · PNGs bleiben unverändert · Zuordnung aus dem Original',
              wraplength=710).pack(anchor='w', pady=(5, 20))
    template = tk.StringVar(value=str(ROOT/'build-play/game/characters/simon-template'))
    candidates = list((ROOT/'artwork-local/import-workspaces').glob('*/workspace.json'))
    candidates += list((ROOT/'artwork-local/import-workspaces').glob('*/project.json'))
    if (READY_ENEMY_WORKSPACE/'project.json').is_file():
        candidates.append(READY_ENEMY_WORKSPACE/'project.json')
    latest = max(candidates, key=lambda p: p.stat().st_mtime).parent if candidates else ''
    workspace = tk.StringVar(value=str(latest))
    status = tk.StringVar(value='Fertige Posen können einzeln importiert werden. Fehlende Bilder bleiben original.')
    built_pack = None
    built_kind = None

    def path_row(label, variable):
        ttk.Label(frame, text=label).pack(anchor='w')
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=(4, 12))
        ttk.Entry(row, textvariable=variable).pack(side='left', fill='x', expand=True)
        def browse():
            chosen = filedialog.askdirectory(parent=root, title=label)
            if chosen:
                variable.set(chosen)
        ttk.Button(row, text='Ordner wählen …', command=browse).pack(side='right', padx=(8, 0))

    path_row('Aufgenommene Spielvorlage (Simon oder Gegner)', template)
    path_row('Arbeitsordner mit fertigen PNGs (Simon oder Gegner)', workspace)
    actions = ttk.Frame(frame)
    actions.pack(fill='x', pady=(8, 12))

    def run(action):
        try:
            action()
        except (OSError, ValueError, KeyError) as error:
            messagebox.showerror('Import angehalten', str(error), parent=root)
            status.set('Vorgang angehalten. Deine Originaldateien bleiben erhalten; Details stehen in der Fehlermeldung.')

    def create():
        parent = filedialog.askdirectory(parent=root, title='Übergeordneten Ordner für die neuen Vorlagen wählen')
        if not parent:
            return
        source = Path(template.get())
        is_enemy = (source/'enemies.json').is_file()
        target = Path(parent)/(('Gegner' if is_enemy else 'Simon')+'-Vorlagen-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        if is_enemy:
            enemy_hd.prepare(source, target)
        else:
            make_workspace(source, target)
        workspace.set(str(target))
        index = target/'VORLAGEN.html'
        webbrowser.open((index if index.is_file() else target).as_uri())
        status.set('Über der Originalvorlage gestalten und PNG im vorgesehenen HD-/artwork-Ordner speichern. Dann „Paket erstellen“.')

    def build():
        nonlocal built_pack, built_kind
        built_pack, built_kind = None, None
        install_button.configure(state='disabled')
        source = Path(workspace.get())
        if (source/'project.json').is_file():
            kind = 'enemy'
            target = ROOT/'artwork-local/enemies'/('gegner-import-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
            try:
                count = enemy_hd.pack(source, target)
            except ValueError as error:
                if 'No changed artwork' in str(error):
                    raise ValueError('Noch kein neues Gegnerbild gefunden. Zuerst ein PNG im Ordner artwork überarbeiten und speichern.') from error
                raise
            enemy_preview(target)
        elif (source/'workspace.json').is_file():
            kind = 'character'
            target = ROOT/'artwork-local/characters'/('simon-import-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
            count = len(import_poses(Path(template.get()), None, target, workspace=source))
        else:
            raise ValueError('Bitte einen vorbereiteten Simon- oder Gegner-Arbeitsordner auswählen.')
        built_pack = target
        built_kind = kind
        install_button.configure(state='normal')
        webbrowser.open((target/'preview.html').as_uri())
        status.set(f'{count} Posen geprüft. Paket: {target}. Noch nicht im Spiel ausgewählt.')
        messagebox.showinfo('Paket vorbereitet',
            f'{count} Posen wurden unverändert übernommen.\n\n{target}\n\n'
            'Im Vorschaufenster stehen Maße und Zuordnungen. Das Spielprofil wurde nicht verändert.', parent=root)

    def install():
        if built_pack is None:
            raise ValueError('Zuerst ein Paket erstellen und im Vorschaufenster prüfen.')
        backup = ROOT/'artwork-local/install-backups'/(built_kind+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        install_pack(built_pack, [ROOT/'build-play/game', ROOT/'build'], backup, kind=built_kind)
        install_button.configure(state='disabled')
        status.set(f'Paket in beiden Spielversionen ausgewählt. Sicherung der alten Auswahl: {backup}')
        messagebox.showinfo('Paket eingebaut',
            'Das neue Paket ist in beiden Spielversionen ausgewählt.\n'
            'Das Spiel vollständig neu starten. Fehlende Posen bleiben original.\n\n'
            f'Sicherung der bisherigen Paketauswahl:\n{backup}', parent=root)

    ttk.Button(actions, text='1. Vorlagenordner anlegen', command=lambda: run(create)).pack(side='left', padx=(0, 10))
    ttk.Button(actions, text='2. Fertige PNGs prüfen / Paket erstellen', command=lambda: run(build)).pack(side='left')
    def browse_poses():
        index = Path(workspace.get())/'VORLAGEN.html'
        if not index.is_file():
            raise ValueError('Zuerst einen Vorlagenordner anlegen oder auswählen.')
        webbrowser.open(index.resolve().as_uri())
    ttk.Button(frame, text='Vorlagen als Bilderübersicht ansehen', command=lambda: run(browse_poses)).pack(anchor='w')
    enemy_workspace = (READY_ENEMY_WORKSPACE if (READY_ENEMY_WORKSPACE/'project.json').is_file()
                       else ROOT/'artwork-local/import-workspaces/skelette-2026-10-23')
    def select_enemies():
        if not (enemy_workspace/'project.json').is_file():
            raise ValueError('Der vorbereitete Skelett-Arbeitsordner ist noch nicht vorhanden.')
        workspace.set(str(enemy_workspace))
        index = enemy_workspace/'VORLAGEN.html'
        webbrowser.open((index if index.is_file() else enemy_workspace).as_uri())
    ttk.Button(frame, text='Vorbereitete Skelett-Bilder öffnen', command=lambda: run(select_enemies)).pack(anchor='w', pady=(6, 0))
    install_button = ttk.Button(frame, text='Paket in beide Spielversionen einbauen', state='disabled', command=lambda: run(install))
    install_button.pack(anchor='w', pady=(10, 0))
    def invalidate_package(*_):
        nonlocal built_pack, built_kind
        built_pack, built_kind = None, None
        install_button.configure(state='disabled')
    workspace.trace_add('write', invalidate_package)
    template.trace_add('write', invalidate_package)
    ttk.Label(frame, text='Photoshop: Original proportional vergrößern, Motiv darüberlegen und PNG exportieren.\n'
              '4,03125× funktioniert genauso wie 10×. Die ursprünglichen Bildränder beibehalten.\n'
              'Doppelte oder nicht zuordenbare Posen werden verständlich gemeldet.',
              wraplength=710).pack(anchor='w', pady=(5, 12))
    ttk.Label(frame, textvariable=status, wraplength=710, foreground='#345a7b').pack(anchor='w', fill='x')
    ttk.Button(frame, text='Anleitung öffnen', command=lambda: webbrowser.open((ROOT/'docs/HD_IMPORT.md').as_uri())).pack(anchor='w', pady=(14, 0))
    root.mainloop()


if __name__ == '__main__':
    main()
