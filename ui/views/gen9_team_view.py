"""Scarlet/Violet My Team preview.

Familiar My Team editor, selected-Pokémon details and box, deliberately
isolated from the Sword/Shield battle, legality, strategy and journey engines.
"""
from __future__ import annotations

import json
from copy import deepcopy
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from uuid import uuid4

import flet as ft
import flet_datatable2 as fdt

from ui.constants import POKEMON_TYPES, TYPE_COLORS
from ui.theme import (
    BORDER_DEFAULT, CARD_RADIUS, PRIMARY_BLUE, SURFACE, SURFACE_RAISED,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_BLUE_SOFT,
    FONT_FAMILY_DISPLAY,
)
from ui.viewmodels.app_state import AppState
from ui.storage.journey_storage import (
    serialize_journey_export, parse_journey_export, journey_export_filename,
)
from ui.rendering import get_sprite_path, asset_exists

ASSETS = Path(__file__).resolve().parents[2] / 'assets'
GEN9_ART = ASSETS / 'raw' / 'pokesprite' / 'pokemon-gen9'
GEN9_BADGES = ASSETS / 'gen9_type_badges'
STAT_KEYS = ('HP', 'ATK', 'DEF', 'SPA', 'SPD', 'SPE')
STAT_NAMES = {'HP':'HP','ATK':'Attack','DEF':'Defense','SPA':'Sp. Atk','SPD':'Sp. Def','SPE':'Speed'}
MOVE_KEYS = ('Move1', 'Move2', 'Move3', 'Move4')
# Match Gen VIII My Team exactly, inserting editable Tera Type beside the
# two natural types.  Auto-population will come with the Gen IX species data.
FIELDS = ('Pokemon','Nickname','Gender','Nature','Type1','Type2','TeraType','Level',
          *STAT_KEYS,*MOVE_KEYS,'Ability','Held Item')
LABELS = {'Pokemon':'Pokémon','Type1':'Primary Type','Type2':'Secondary Type',
          'TeraType':'Tera Type','ATK':'ATK','DEF':'DEF','SPA':'SPA','SPD':'SPD','SPE':'SPE',
          'Held Item':'Held Item', **{f'Move{i}':f'Move {i}' for i in range(1,5)}}
# Only these are editable as numeric values. Avoid Gen VIII stat estimates.
NUMERIC = set(STAT_KEYS) | {'Level'}
GENDER_OPTIONS = ('Male', 'Female', 'Genderless')
NATURE_OPTIONS = (
    'Adamant', 'Bashful', 'Bold', 'Brave', 'Calm', 'Careful', 'Docile',
    'Gentle', 'Hardy', 'Hasty', 'Impish', 'Jolly', 'Lax', 'Lonely', 'Mild',
    'Modest', 'Naive', 'Naughty', 'Quiet', 'Quirky', 'Rash', 'Relaxed',
    'Sassy', 'Serious', 'Timid',
)


def artwork_path(name: str, *, gender: str | None = None, nature: str | None = None, held_item: str | None = None) -> Path | None:
    """Prefer Gen IX HOME artwork; reuse established Gen VIII form-aware lookup.

    Never ask Gen VIII's identity resolver to validate a newly introduced species.
    """
    from ui.rendering import slugify_pokemon_name
    if not name.strip():
        return None
    slug = slugify_pokemon_name(name.strip())
    candidate = GEN9_ART / f'{slug}-texture.png'
    if asset_exists(candidate):
        return candidate
    return get_sprite_path(name, gender=gender, nature=nature,
                           held_item=held_item, use_texture=True)


class Gen9TeamView:
    def __init__(self, page: ft.Page, *, app_state: AppState, on_start_new_journey=None, on_journey_loaded=None):
        self.page, self.app_state = page, app_state
        self.on_start_new_journey = on_start_new_journey
        self.on_journey_loaded = on_journey_loaded
        self.party = deepcopy(app_state.team_data)
        self.box = deepcopy(app_state.box_data)
        self.saved_party, self.saved_box = deepcopy(self.party), deepcopy(self.box)
        self.selected, self.show_box = 0, False
        self.fields: dict[str, ft.Control] = {}
        # Controls stay mounted while the user edits; never rebuild on blur.
        self.editor_controls: dict[tuple[int, str], ft.Control] = {}
        self.box_selected = 0
        self.show_nicknames = True
        self.status = ft.Text('', color=TEXT_SECONDARY, size=13)
        self.host = ft.Container()
        # Existing move metadata is display-only in the Gen IX preview.
        # Never invoke legality checks or damage/strategy evaluation.
        self.move_types = self._read_move_types()

    @property
    def has_unsaved_changes(self) -> bool:
        if self.party != self.saved_party or self.box != self.saved_box:
            return True
        rows = self._list()
        if 0 <= self.selected < len(rows):
            row = rows[self.selected]
            for key, field in self.fields.items():
                current = str(field.value or '').strip()
                stored = row.get(key)
                if current != ('' if stored is None else str(stored)):
                    return True
        return False

    def discard_unsaved_changes(self) -> None:
        self.party, self.box = deepcopy(self.saved_party), deepcopy(self.saved_box)
        self.selected, self.show_box = 0, False
        self._render()
        self.page.update()

    def build(self) -> ft.Control:
        self._render()
        return self.host

    def _list(self) -> list[dict]:
        return self.box if self.show_box else self.party

    def _commit(self) -> bool:
        rows = self._list()
        if not (0 <= self.selected < len(rows)):
            return True
        row = rows[self.selected]
        for key, field in self.fields.items():
            raw = str(field.value or '').strip()
            if key in NUMERIC:
                if raw and (not raw.isdecimal() or (key=='Level' and not 1 <= int(raw) <= 100)
                            or (key!='Level' and not 0 <= int(raw) <= 999)):
                    self.status.value = f'{LABELS.get(key,key)} must be a valid number.'
                    self.status.color = '#F87171'
                    self.page.update()
                    return False
                row[key] = int(raw) if raw else None
            else:
                row[key] = raw or None
        if row.get('Pokemon') and not row.get('MemberID'):
            row['MemberID'] = f'pkm_{uuid4().hex}'
        self.status.value = 'Unsaved changes — select Save Team to keep these details.'
        self.status.color = TEXT_SECONDARY
        return True

    def _select(self, index: int, boxed: bool) -> None:
        if not self._commit(): return
        self.show_box, self.selected = boxed, index
        self._render()
        self.page.update()

    def _add(self, event=None) -> None:
        if not self._commit(): return
        if len(self.party) < 6:
            self.show_box = False
            self.party.append({'Pokemon':None, 'Level':None, 'MemberID':f'pkm_{uuid4().hex}'})
        else:
            self.show_box = True
            self.box.append({'Pokemon':None, 'Level':None, 'MemberID':f'pkm_{uuid4().hex}'})
        self.selected = len(self._list()) - 1
        self._render(); self.page.update()

    def _transfer(self, event=None) -> None:
        if not self._commit(): return
        rows = self._list()
        if not 0 <= self.selected < len(rows): return
        if self.show_box and len(self.party) >= 6:
            self.status.value = 'The active party already has six Pokémon.'
            self.page.update(); return
        pokemon = rows.pop(self.selected)
        other = self.party if self.show_box else self.box
        other.append(pokemon)
        self.show_box = not self.show_box
        self.selected = len(other)-1
        self._render(); self.page.update()

    def _swap(self, index: int) -> None:
        if not self._commit(): return
        if not (self.show_box and self.box and self.party and 0 <= index < len(self.party)): return
        self.box[self.selected], self.party[index] = self.party[index], self.box[self.selected]
        self._render(); self.page.update()

    def _request_swap(self, event=None) -> None:
        if not self._commit(): return
        if not self.show_box or not self.box or not self.party: return
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text('Swap with party Pokémon'),
            content=ft.Column([
                ft.OutlinedButton(
                    f'{index+1}. {row.get("Nickname") or row.get("Pokemon") or "Unknown"}',
                    on_click=lambda e, idx=index: (self.page.pop_dialog(), self._swap(idx)))
                for index,row in enumerate(self.party)
            ], tight=True),
            actions=[ft.TextButton('Cancel', on_click=lambda e:self.page.pop_dialog())],
        )
        self.page.show_dialog(dialog)

    def _request_remove(self, event=None) -> None:
        if not self._commit(): return
        rows=self._list()
        if not 0 <= self.selected < len(rows): return
        name=rows[self.selected].get('Nickname') or rows[self.selected].get('Pokemon') or 'this Pokémon'
        def confirm(event=None):
            self.page.pop_dialog()
            rows.pop(self.selected)
            self.selected=max(0,min(self.selected,len(rows)-1))
            self._render(); self.page.update()
        self.page.show_dialog(ft.AlertDialog(modal=True,
            title=ft.Text('Release Pokémon?'),
            content=ft.Text(f'Remove {name} from this Journey?'),
            actions=[ft.TextButton('Cancel',on_click=lambda e:self.page.pop_dialog()),
                     ft.Button('Remove',on_click=confirm)]))

    async def _save(self, event=None) -> None:
        if not self._commit(): return
        for record in self.party + self.box:
            for key in NUMERIC:
                value = record.get(key)
                if value in (None, ''): continue
                if not str(value).isdecimal() or (key == 'Level' and not 1 <= int(value) <= 100) or (key != 'Level' and not 0 <= int(value) <= 999):
                    self.status.value = f'{LABELS.get(key,key)} must be a valid number.'
                    self.status.color = '#F87171'
                    self.page.update()
                    return
        if any(not str(row.get('Pokemon') or '').strip() for row in self.party+self.box):
            self.status.value = 'Enter a species for each occupied slot before saving.'
            self.status.color = '#F87171'; self.page.update(); return
        if await self.app_state.save_gen9_tracker(self.party,self.box):
            self.party=deepcopy(self.app_state.team_data)
            self.box=deepcopy(self.app_state.box_data)
            self.saved_party,self.saved_box=deepcopy(self.party),deepcopy(self.box)
            self.status.value='Team saved.'
            self.status.color='#4ADE80'
        else:
            self.status.value='Save failed; previous Journey retained.'
            self.status.color='#F87171'
        self._render(); self.page.update()

    async def _export_journey(self, event=None) -> None:
        if self.has_unsaved_changes:
            self.status.value = 'Save or discard changes before exporting.'
            self.status.color = '#FFE5A3'; self.page.update(); return
        try:
            try: app_version = version('pokemon-battle-compass')
            except PackageNotFoundError: app_version = '0.3.1'
            serialized = serialize_journey_export(
                self.app_state.get_journey_export_copy(), app_version=app_version)
            await ft.FilePicker().save_file(
                dialog_title='Export Journey', file_name=journey_export_filename(),
                file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=['json'],
                src_bytes=serialized.encode('utf-8'))
            self.status.value = 'Journey export requested.'
            self.status.color = TEXT_SECONDARY
        except (OSError, RuntimeError, ValueError) as error:
            self.status.value = f'Export failed: {error}'
            self.status.color = '#F87171'
        self.page.update()

    async def _load_journey(self, event=None) -> None:
        if self.has_unsaved_changes:
            self.status.value = 'Save or discard changes before loading a Journey.'
            self.status.color = '#FFE5A3'; self.page.update(); return
        if self.page.web:
            self.status.value = 'In the web version, use the Journey import page.'
            self.page.update()
            return
        try:
            selections = await ft.FilePicker().pick_files(
                dialog_title='Load Journey',allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=['json'],
                with_data=True,cancel_upload_on_window_blur=False)
            if not selections: return
            selected=selections[0]
            if selected.bytes is not None:
                raw=selected.bytes.decode('utf-8')
            elif selected.path:
                raw=Path(selected.path).read_text(encoding='utf-8')
            else:
                raise ValueError('The selected file could not be read.')
            parsed=parse_journey_export(raw)
            if parsed.status != 'valid' or parsed.journey is None:
                raise ValueError(parsed.error or 'Invalid Journey export.')
            incoming=parsed.journey
            incoming_game = incoming.get('game', 'Sword')
        except (OSError, UnicodeError, ValueError, RuntimeError) as error:
            self.status.value = f'Load failed: {error}'
            self.status.color = '#F87171'; self.page.update(); return

        async def confirm(event=None):
            self.page.pop_dialog()
            if await self.app_state.import_journey(incoming):
                # The saved Journey, not the previous screen, determines the game.
                if self.app_state.game != incoming_game:
                    self.status.value = (
                        f'Journey saved, but expected {incoming_game} and found '
                        f'{self.app_state.game}. Restart the application to reload it.'
                    )
                    self.status.color = '#F87171'
                    self._render(); self.page.update()
                    return
                # Switching Sword/Shield <-> Scarlet/Violet must reconstruct
                # AppShell: its game-specific views are chosen at build time.
                if self.on_journey_loaded is not None:
                    self.on_journey_loaded()
                    return
                self.party=deepcopy(self.app_state.team_data)
                self.box=deepcopy(self.app_state.box_data)
                self.saved_party,self.saved_box=deepcopy(self.party),deepcopy(self.box)
                self.selected,self.show_box=0,False
                self.status.value='Journey loaded.'
                self.status.color='#4ADE80'
            else:
                self.status.value='Could not save imported Journey.'
                self.status.color='#F87171'
            self._render(); self.page.update()

        self.page.show_dialog(ft.AlertDialog(modal=True,
            title=ft.Text('Replace current Journey?'),
            content=ft.Text(
                f'Load the Pokémon {incoming_game} Journey? This replaces the '
                'current saved team and box and switches to that game.'),
            actions=[ft.TextButton('Cancel',on_click=lambda e:self.page.pop_dialog()),
                     ft.Button('Load Journey',on_click=confirm)]))

    def _field(self, key: str, row: dict) -> ft.Control:
        """Box editing uses the same explicit controls as party editing."""
        value = str(row.get(key) or '')
        if key == 'Gender':
            options = GENDER_OPTIONS
            control = ft.Dropdown(
                label=LABELS.get(key, key),
                value=value if value in options else None,
                options=[ft.DropdownOption(key=option, text=option)
                         for option in options],
                width=138, dense=True, text_size=12,
            )
        elif key == 'Nature':
            control = ft.AutoComplete(
                value=value,
                suggestions=self._nature_suggestions(value),
                suggestions_max_height=240,
                width=138,
            )
        else:
            control = ft.TextField(
                label=LABELS.get(key, key), value=value,
                width=138 if key not in ('Pokemon','Nickname','Ability','Held Item') else 186,
                dense=True,
                keyboard_type=(ft.KeyboardType.NUMBER if key in NUMERIC
                               else ft.KeyboardType.TEXT),
            )
        self.fields[key] = control
        return control

    def _image(self,row:dict,size:int=128) -> ft.Control:
        name=str(row.get('Pokemon') or '')
        path=artwork_path(name, gender=row.get('Gender'),nature=row.get('Nature'), held_item=row.get('Held Item'))
        if path is None:
            return ft.Container(content=ft.Text('?',size=35,color=TEXT_MUTED),
                width=size,height=size,alignment=ft.Alignment.CENTER,bgcolor=SURFACE)
        return ft.Image(src=path.relative_to(ASSETS).as_posix(),width=size,height=size,
                        fit=ft.BoxFit.CONTAIN,semantics_label=name)

    def _type_badge(self, value: str | None, label: str = '') -> ft.Control:
        name = str(value or '').strip().title()
        if name not in POKEMON_TYPES:
            return ft.Text(f'{label}: —' if label else '—', color=TEXT_MUTED, size=13)
        filename = f'{name.lower()}{"-tera" if label == "TERA" else ""}.png'
        path = GEN9_BADGES / filename
        if asset_exists(path):
            badge = ft.Image(src=f'gen9_type_badges/{filename}', height=27,
                             fit=ft.BoxFit.CONTAIN,
                             semantics_label=f'{name} {"Tera " if label == "TERA" else ""}type')
            return badge
        return ft.Container(content=ft.Text(name.upper(),
                color='#FFFFFF',weight=ft.FontWeight.BOLD,size=12),
                bgcolor=TYPE_COLORS[name],border_radius=5,
                padding=ft.Padding.symmetric(horizontal=10,vertical=5))

    def _record_name(self,row:dict) -> str:
        return str((row.get('Nickname') if self.show_nicknames else None) or row.get('Pokemon') or 'New Pokémon')

    def _table_change(self, index: int, key: str, value: str | None) -> None:
        """Change only the in-memory draft; storage changes at Save Team."""
        if not 0 <= index < len(self.party):
            return
        value = str(value or '').strip()
        if key in NUMERIC:
            # Permit an empty/incomplete number while editing. Save validates it.
            self.party[index][key] = int(value) if value.isdecimal() else (value or None)
        else:
            self.party[index][key] = value or None
        self.status.value = 'Unsaved changes — select Save Team to keep these details.'
        self.status.color = TEXT_SECONDARY

    async def _focus_next_numeric_field(self, row_index: int, key: str) -> None:
        """Enter advances Level -> HP -> ... -> Speed -> next Level."""
        numeric_order = ('Level', *STAT_KEYS)
        if key not in numeric_order:
            return
        position = row_index * len(numeric_order) + numeric_order.index(key) + 1
        if position >= len(self.party) * len(numeric_order):
            return
        target_row, target_key_idx = divmod(position, len(numeric_order))
        target = self.editor_controls.get((target_row, numeric_order[target_key_idx]))
        if isinstance(target, ft.TextField):
            await target.focus()

    def _table_submit(self, index: int, key: str, value: str) -> None:
        """Enter advances focus; never persists or rebuilds the table."""
        self._table_change(index, key, value)
        if key in ('Level', *STAT_KEYS):
            self.page.run_task(self._focus_next_numeric_field, index, key)

    @staticmethod
    def _nature_suggestions(query: str) -> list[ft.AutoCompleteSuggestion]:
        """Small type-to-search list matching Gen VIII Nature entry."""
        query = str(query or '').strip().casefold()
        if not query:
            return []
        matches = ([nature for nature in NATURE_OPTIONS
                    if nature.casefold().startswith(query)] +
                   [nature for nature in NATURE_OPTIONS
                    if query in nature.casefold() and
                    not nature.casefold().startswith(query)])[:8]
        return [ft.AutoCompleteSuggestion(key=nature, value=nature)
                for nature in matches]

    def _nature_change(self, index: int, control: ft.AutoComplete) -> None:
        """Update draft and suggestions without rebuilding the table."""
        value = str(control.value or '')
        self._table_change(index, 'Nature', value)
        control.suggestions = self._nature_suggestions(value)
        control.update()

    def _build_editor_control(self, index: int, key: str, value: object) -> ft.Control:
        """Use Gen VIII's visible edit controls, not borderless display text."""
        current = '' if value is None else str(value)
        if key == 'Gender':
            return ft.Dropdown(
                value=current if current in GENDER_OPTIONS else None,
                options=[ft.DropdownOption(key=option, text=option)
                         for option in GENDER_OPTIONS],
                width=115, dense=True, text_size=12,
                on_select=lambda event, i=index, k=key:
                    self._table_change(i, k, event.control.value),
            )
        if key == 'Nature':
            return ft.AutoComplete(
                value=current,
                suggestions=self._nature_suggestions(current),
                suggestions_max_height=240,
                width=115,
                on_change=lambda event, i=index:
                    self._nature_change(i, event.control),
                on_select=lambda event, i=index:
                    self._table_change(i, 'Nature', event.control.value),
            )
        widths = {'Pokemon':125, 'Nickname':152, 'Type1':105, 'Type2':105,
                  'TeraType':105, 'Ability':145, 'Held Item':145,
                  **{move:150 for move in MOVE_KEYS}}
        width = widths.get(key, 64 if key in NUMERIC else 125)
        return ft.TextField(
            value=current, width=width, dense=True, text_size=12,
            hint_text='Optional nickname' if key == 'Nickname' else None,
            text_align=ft.TextAlign.RIGHT if key in NUMERIC else ft.TextAlign.LEFT,
            keyboard_type=(ft.KeyboardType.NUMBER if key in NUMERIC
                           else ft.KeyboardType.TEXT),
            input_filter=(ft.InputFilter(allow=True, regex_string=r'^[0-9]*$',
                                         replacement_string='')
                          if key in NUMERIC else None),
            # Do not use on_blur to rebuild: focus must remain stable.
            on_change=lambda event, i=index, k=key:
                self._table_change(i, k, event.control.value),
            on_submit=lambda event, i=index, k=key:
                self._table_submit(i, k, event.control.value),
        )

    def _build_team_table(self) -> ft.Control:
        """Gen VIII's visibly editable table and single-Tab focus behavior."""
        widths = {'Pokemon':134,'Nickname':160,'Gender':120,'Nature':130,
                  'Level':76,'Type1':116,'Type2':116,'TeraType':116,
                  'Ability':166,'Held Item':166,
                  **{key:76 for key in STAT_KEYS},
                  **{key:166 for key in MOVE_KEYS}}
        columns = [key for key in FIELDS if key != 'Nickname' or self.show_nicknames]
        rows = []
        self.editor_controls = {}
        for index, record in enumerate(self.party):
            cells = []
            for key in columns:
                editor = self._build_editor_control(index, key, record.get(key))
                self.editor_controls[(index, key)] = editor
                # The pinned Pokémon cell has the same divider as Gen VIII.
                if key == 'Pokemon':
                    editor = ft.Container(
                        content=editor, padding=ft.Padding.only(right=7),
                        border=ft.Border.only(right=ft.BorderSide(1, BORDER_DEFAULT)),
                    )
                cells.append(ft.DataCell(editor))
            # Do not make rows selectable: selectable rows introduce an extra
            # focus stop between text fields in DataTable2 (double Tab).
            rows.append(ft.DataRow(cells=cells))
        return fdt.DataTable2(
            columns=[fdt.DataColumn2(label=ft.Text(LABELS.get(key,key),
                size=14,weight=ft.FontWeight.BOLD,color=TEXT_PRIMARY),
                fixed_width=widths[key]) for key in columns],
            rows=rows,fixed_left_columns=1,fixed_top_rows=1,
            fixed_columns_color=SURFACE,fixed_corner_color=SURFACE_RAISED,
            min_width=sum(widths[key] for key in columns),
            column_spacing=8,horizontal_margin=8,data_row_height=58,
            heading_row_height=46,
            border=ft.Border.all(1,BORDER_DEFAULT),border_radius=12,
            heading_row_color=SURFACE_RAISED,
        )

    def _refresh_selected_detail(self, index: int) -> None:
        if self.show_box or self.selected!=index:
            return
        # Never update the page on blur: it can consume the next Tab key.
        # The details refresh when selection changes or Save Team is pressed.

    def _selector_buttons(self,records:list[dict],boxed:bool) -> list[ft.Control]:
        result=[]
        for index,row in enumerate(records):
            active=self.show_box==boxed and self.selected==index
            result.append(ft.Container(
                content=ft.Column([
                    self._image(row,75),
                    ft.Text(self._record_name(row),weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,text_align=ft.TextAlign.CENTER,size=13),
                    ft.Text(f'Lv. {row.get("Level") or "—"}',color=TEXT_SECONDARY,size=12),
                ],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=3),
                padding=9,width=146,bgcolor=SURFACE_RAISED,border_radius=10,
                border=ft.Border.all(2 if active else 1,PRIMARY_BLUE if active else BORDER_DEFAULT),
                on_click=lambda e,i=index,b=boxed:self._select(i,b)))
        return result

    @staticmethod
    def _read_move_types() -> dict[str, str]:
        path = Path(__file__).resolve().parents[2] / 'data' / 'moves.json'
        try:
            with path.open(encoding='utf-8') as source:
                moves = json.load(source)
            return {
                str(move['Move']).casefold(): str(move['Type'])
                for move in moves
                if isinstance(move, dict) and move.get('Move') and
                str(move.get('Type') or '') in POKEMON_TYPES
            }
        except (FileNotFoundError, OSError, ValueError, TypeError):
            return {}

    # Gen IX details retain the Gen VIII card structure and styling. The only
    # intentional difference in the header is an additional Tera Type line.
    # No Gen VIII battle, evolution, or legality helpers are invoked here.
    _NATURE_EFFECTS = {
        'Hardy': (None, None), 'Lonely': ('ATK', 'DEF'),
        'Brave': ('ATK', 'SPE'), 'Adamant': ('ATK', 'SPA'),
        'Naughty': ('ATK', 'SPD'), 'Bold': ('DEF', 'ATK'),
        'Docile': (None, None), 'Relaxed': ('DEF', 'SPE'),
        'Impish': ('DEF', 'SPA'), 'Lax': ('DEF', 'SPD'),
        'Timid': ('SPE', 'ATK'), 'Hasty': ('SPE', 'DEF'),
        'Serious': (None, None), 'Jolly': ('SPE', 'SPA'),
        'Naive': ('SPE', 'SPD'), 'Modest': ('SPA', 'ATK'),
        'Mild': ('SPA', 'DEF'), 'Quiet': ('SPA', 'SPE'),
        'Bashful': (None, None), 'Rash': ('SPA', 'SPD'),
        'Calm': ('SPD', 'ATK'), 'Gentle': ('SPD', 'DEF'),
        'Sassy': ('SPD', 'SPE'), 'Careful': ('SPD', 'SPA'),
        'Quirky': (None, None),
    }
    _STAT_COLORS = {
        'HP': '#4ADE80', 'ATK': '#F87171', 'DEF': '#FBBF24',
        'SPA': '#A78BFA', 'SPD': '#60A5FA', 'SPE': '#F472B6',
    }

    def _detail_selector(self) -> ft.Control:
        options = []
        for source, records in (('party', self.party), ('box', self.box)):
            for index, row in enumerate(records):
                name = self._record_name(row)
                options.append(ft.DropdownOption(
                    key=f'{source}:{index}',
                    text=f'{"Party" if source == "party" else "Box"} · {name}',
                ))
        value = f'{"box" if self.show_box else "party"}:{self.selected}'
        if not options:
            return ft.Container()
        return ft.Dropdown(
            label='Select Pokémon',
            value=value,
            options=options,
            width=360,
            on_select=self._detail_selected,
        )

    def _detail_selected(self, event) -> None:
        value = str(event.control.value or '')
        try:
            source, index = value.split(':', 1)
            index = int(index)
        except (ValueError, TypeError):
            return
        if source == 'party' and 0 <= index < len(self.party):
            self._select(index, False)
        elif source == 'box' and 0 <= index < len(self.box):
            self._select(index, True)

    def _nature_summary(self, row: dict) -> ft.Control:
        nature = str(row.get('Nature') or '').strip().title()
        if nature not in self._NATURE_EFFECTS:
            return ft.Text('Nature: —', size=14, color=TEXT_MUTED)
        higher, lower = self._NATURE_EFFECTS[nature]
        controls = [ft.Text(f'Nature: {nature},', size=14,
                            weight=ft.FontWeight.BOLD, color=TEXT_SECONDARY)]
        if higher is None or lower is None:
            controls.append(ft.Text('Neutral', size=14, weight=ft.FontWeight.BOLD,
                                    color=TEXT_MUTED))
        else:
            controls.extend([
                ft.Icon(ft.Icons.ARROW_UPWARD_ROUNDED, size=17, color='#F87171'),
                ft.Text(higher, size=14, weight=ft.FontWeight.BOLD, color='#F87171'),
                ft.Text('/', size=14, color=TEXT_MUTED),
                ft.Icon(ft.Icons.ARROW_DOWNWARD_ROUNDED, size=17, color='#60A5FA'),
                ft.Text(lower, size=14, weight=ft.FontWeight.BOLD, color='#60A5FA'),
            ])
        return ft.Row(controls, spacing=4, tight=True, wrap=True,
                      vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _stat_row(self, key: str, value: object, nature: str) -> ft.Control:
        try:
            number = int(value) if value is not None else 0
        except (ValueError, TypeError):
            number = 0
        up, down = self._NATURE_EFFECTS.get(nature, (None, None))
        value_color = ('#F87171' if key == up else '#60A5FA'
                       if key == down else TEXT_PRIMARY)
        return ft.Row([
            ft.Text(key, width=44, weight=ft.FontWeight.BOLD,
                    color=TEXT_SECONDARY),
            ft.ProgressBar(value=min(1.0, max(0.0, number / 300)),
                           expand=True, height=10,
                           color=self._STAT_COLORS[key], bgcolor='#22FFFFFF',
                           border_radius=6),
            ft.Text(str(number) if value not in (None, '') else '—',
                    width=40, text_align=ft.TextAlign.RIGHT,
                    weight=ft.FontWeight.BOLD, color=value_color),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _move_cards(self, row: dict) -> ft.Control:
        # Only known move types get Gen VIII-style coloring; no legality or
        # damage evaluation, and unfamiliar Gen IX moves remain neutral.
        cards = []
        for key in MOVE_KEYS:
            name = str(row.get(key) or '').strip()
            move_type = self.move_types.get(name.casefold())
            elements = [ft.Text(name or 'Empty move slot', size=16,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT_PRIMARY if name else TEXT_SECONDARY,
                                expand=True)]
            if move_type:
                elements.append(self._type_badge(move_type))
            card = ft.Container(
                content=ft.Row(elements, spacing=8,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=14, bgcolor=TYPE_COLORS.get(move_type, '#4B5563'),
                opacity=1.0 if name else 0.55, border_radius=10,
            )
            cards.append(ft.Container(content=card, col={'xs': 12, 'sm': 6}))
        return ft.ResponsiveRow(cards, columns=12, spacing=12, run_spacing=12)

    def _detail_footer(self, row: dict) -> ft.Control:
        ability = str(row.get('Ability') or '—')
        item = str(row.get('Held Item') or '—')
        ability_card = ft.Container(content=ft.Column([
            ft.Text('Ability', size=13, color=TEXT_MUTED),
            ft.Text(ability, size=18, weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY),
        ], spacing=4), height=80, padding=14,
            bgcolor=PRIMARY_BLUE_SOFT, border_radius=10)
        item_card = ft.Container(content=ft.Column([
            ft.Text('Held Item', size=13, color=TEXT_MUTED),
            ft.Text(item, size=18, weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY),
        ], spacing=4), height=80, padding=14,
            bgcolor=SURFACE, border_radius=10)
        return ft.ResponsiveRow([
            ft.Container(content=ability_card, col={'xs': 12, 'sm': 6}),
            ft.Container(content=item_card, col={'xs': 12, 'sm': 6}),
        ], columns=12, spacing=12, run_spacing=12)

    def _detail(self, row: dict) -> ft.Control:
        name = str(row.get('Pokemon') or 'Unknown')
        gender = str(row.get('Gender') or '').strip().lower()
        name_controls = [ft.Text(name, size=32, weight=ft.FontWeight.BOLD,
                                 font_family=FONT_FAMILY_DISPLAY,
                                 color=TEXT_PRIMARY)]
        if gender in ('male', 'female'):
            name_controls.append(ft.Icon(
                ft.Icons.FEMALE if gender == 'female' else ft.Icons.MALE,
                size=22, color='#FF5BA7' if gender == 'female' else PRIMARY_BLUE))

        types = [self._type_badge(row.get('Type1')),
                 self._type_badge(row.get('Type2'))]
        header = ft.ResponsiveRow([
            ft.Container(content=self._image(row, 170),
                         col={'xs': 12, 'sm': 4},
                         alignment=ft.Alignment.CENTER),
            ft.Container(content=ft.Column([
                ft.Row(name_controls, spacing=6,
                       alignment=ft.MainAxisAlignment.CENTER,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row(types, spacing=8, tight=True,
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Text(f'Lv. {row.get("Level") or "—"}', size=18,
                        color=TEXT_SECONDARY),
                ft.Row([ft.Text('Tera Type', size=13, color=TEXT_SECONDARY),
                        self._type_badge(row.get('TeraType'), 'TERA')],
                       spacing=8, tight=True,
                       alignment=ft.MainAxisAlignment.CENTER),
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                col={'xs': 12, 'sm': 8}, alignment=ft.Alignment.CENTER),
        ], columns=12, spacing=16, run_spacing=12,
           vertical_alignment=ft.CrossAxisAlignment.CENTER)
        nature = str(row.get('Nature') or '').strip().title()
        return ft.Container(
            content=ft.Column([
                header,
                ft.Divider(color=BORDER_DEFAULT, height=1),
                ft.ResponsiveRow([
                    ft.Container(content=ft.Text('Stats', size=19,
                        weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        col={'xs': 12, 'sm': 4},
                        alignment=ft.Alignment.CENTER_LEFT),
                    ft.Container(content=self._nature_summary(row),
                        col={'xs': 12, 'sm': 8},
                        alignment=ft.Alignment.CENTER_RIGHT),
                ], columns=12, spacing=12, run_spacing=8,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Column([self._stat_row(key, row.get(key), nature)
                           for key in STAT_KEYS], spacing=9),
                ft.Column([
                    ft.Text('Moves', size=19, weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY),
                    ft.Text('Move details are coming with Gen IX support.',
                            size=13, color=TEXT_MUTED, expand=True),
                ], spacing=3),
                self._move_cards(row),
                self._detail_footer(row),
            ], spacing=16),
            padding=20, bgcolor=SURFACE_RAISED, border_radius=16,
        )

    def _panel(self,title:str,controls:list[ft.Control],width:int=1280) -> ft.Control:
        return ft.Container(content=ft.Column([
            ft.Text(title,size=29,weight=ft.FontWeight.BOLD,color=TEXT_PRIMARY),*controls,
        ],spacing=16),width=width,padding=22,bgcolor=SURFACE,
            border=ft.Border.all(1,BORDER_DEFAULT),border_radius=CARD_RADIUS)

    def _render(self) -> None:
        self.fields={}
        rows=self._list()
        if self.selected>=len(rows): self.selected=max(0,len(rows)-1)
        selected=rows[self.selected] if rows and self.selected>=0 else None
        editor=[]
        editor.append(ft.Text('Update a level, stat, move, or item below, then save. Gen IX battle features are coming soon.',color=TEXT_SECONDARY))
        editor.append(ft.Text('Swipe horizontally to view additional fields.',size=12,color=TEXT_MUTED,italic=True))
        editor.append(self._build_team_table())
        if selected is not None and self.show_box:
            editor.append(ft.Text('Editing boxed Pokémon',size=17,weight=ft.FontWeight.BOLD))
            editor.append(ft.Row([self._field(key,selected) for key in ('Pokemon','Nickname','Gender','Nature','Type1','Type2','TeraType','Level')],
                                 spacing=10,scroll=ft.ScrollMode.AUTO))
            editor.append(ft.Row([self._field(key,selected) for key in STAT_KEYS],
                                 spacing=10,scroll=ft.ScrollMode.AUTO))
            editor.append(ft.Row([self._field(key,selected) for key in MOVE_KEYS],
                                 spacing=10,scroll=ft.ScrollMode.AUTO))
        editor.append(ft.Row([
            ft.Button('Add Pokémon',icon=ft.Icons.ADD,on_click=self._add),
            ft.Button('Save Team',icon=ft.Icons.SAVE,on_click=self._save,bgcolor=PRIMARY_BLUE,color='#FFFFFF'),
            ft.OutlinedButton('Discard Changes',on_click=lambda e:self.discard_unsaved_changes()),
            ft.OutlinedButton('Export Journey',on_click=self._export_journey),
            ft.OutlinedButton('Load Journey',on_click=self._load_journey),
            *([ft.OutlinedButton('Start New Journey', on_click=lambda e: self.on_start_new_journey())]
              if self.on_start_new_journey is not None else []),
        ],spacing=12,wrap=True))
        editor.append(self.status)
        details=([self._detail_selector(), self._detail(selected)]
                 if selected is not None else
                 [ft.Text('Select or add a Pokémon to see its details.', color=TEXT_SECONDARY)])
        box=[ft.Text('Select a Pokémon to view its details or move it to the party.',color=TEXT_SECONDARY)]
        box.append(ft.Row(self._selector_buttons(self.box,True) or [ft.Text('Your Box is empty.',color=TEXT_MUTED)],wrap=True,spacing=8))
        if selected is not None:
            box.append(ft.Row([
                ft.OutlinedButton('Move to Party' if self.show_box else 'Move to Box',on_click=self._transfer),
                *([ft.OutlinedButton('Swap with Party',on_click=self._request_swap)] if self.show_box and len(self.party)>=6 else []),
                ft.OutlinedButton('Release Pokémon',on_click=self._request_remove),
            ],wrap=True,spacing=12))
        content=[self._panel('Manage My Team',editor),self._panel('Pokémon Details',details,940),
                 self._panel('Box',box,1280)]
        self.host.content=ft.Column(content,spacing=24,horizontal_alignment=ft.CrossAxisAlignment.CENTER)
