import json
import os.path
import re
from dataclasses import dataclass
from typing import Iterable, List

from .anki import (
    AnkiAddonData, AnkiCollection, AnkiModelNotes, is_anki_package_installed,
)
from .anki_format import make_anki_note
from .model import AnkiNote, JsonData
from .roam import extract_roam_blocks, load_roam_pages

if is_anki_package_installed():
    from anki.utils import stripHTMLMedia
else:
    # allow running tests without anki package installed
    # noinspection PyPep8Naming
    def stripHTMLMedia(content): return content


@dataclass
class AnkiNoteImporter:
    addon_data: AnkiAddonData
    collection: AnkiCollection

    def import_from_path(self, path: str) -> str:
        roam_pages = load_roam_pages(path)
        roam_notes = extract_roam_blocks(roam_pages)

        num_notes_added = 0
        num_notes_ignored = 0

        config = self.addon_data.read_config()
        graph = config['graph.name']
        model_notes = self.collection.get_model_notes(
            config['model.name'],
            config['fields.text'],
            config['fields.roam.source'],
            config['fields.roam.block.id'],
            config['fields.roam.graph'],
            config['fields.roam.text'],
            config['deck.name'],
        )
        note_adder = AnkiNoteAdder(model_notes, config)

        for roam_note in roam_notes:
            note = make_anki_note(roam_note, graph)
            if note_adder.try_add(note):
                num_notes_added += 1
            else:
                num_notes_ignored += 1

        def info():
            if not num_notes_added and not num_notes_ignored:
                yield 'No notes found'
                return

            if num_notes_added:
                yield f'{num_notes_added} notes added or updated'

            if num_notes_ignored:
                yield f'{num_notes_ignored} notes were imported before and were not imported again'

        return ', '.join(info()) + '.'


class AnkiNoteAdder:
    def __init__(
        self,
        model_notes: AnkiModelNotes,
        config: JsonData,
    ):
        self.model_notes = model_notes
        self.config = config
        self.existing_block_ids = dict(model_notes.get_block_ids())

    def try_add(self, anki_note: AnkiNote) -> bool:
        return self.model_notes.add_or_update_note(anki_note, self.config, self.existing_block_ids)
