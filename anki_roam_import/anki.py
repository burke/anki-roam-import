import os
from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable, Optional, Dict

from .model import JsonData, AnkiNote


def is_anki_package_installed() -> bool:
    try:
        import anki
    except ModuleNotFoundError:
        return False
    else:
        return True


if is_anki_package_installed():
    from anki.collection import _Collection
    from anki.models import NoteType
    from anki.notes import Note
    from anki.utils import splitFields
    from aqt.main import AnkiQt
else:
    # allow running tests without anki package installed
    from typing import Any, Dict

    _Collection = Any
    NoteType = Dict[str, Any]
    AnkiQt = Any

    class Note:
        def __init__(self, collection, model):
            self.fields = []

    # noinspection PyPep8Naming
    def splitFields(fields):
        return []


@dataclass
class AnkiModelNotes:
    collection: _Collection
    model: NoteType
    block_id_field_index: int
    config: JsonData

    # return: was new note created?
    # TODO(burke) could do tri-state here: NEW, UPDATE, NONE
    def add_or_update_note(self, note: AnkiNote, config: JsonData, existing_block_ids: Dict[str, int]) -> bool:
        if note.roam_block_id in existing_block_ids:
            note_id = existing_block_ids[note.roam_block_id]
            existing_note = self.collection.getNote(note_id)
            updated = False

            f_text = config["fields.text"]
            f_roam_text = config["fields.roam.text"]
            f_roam_source = config["fields.roam.source"]
            f_roam_graph = config["fields.roam.graph"]
            f_roam_page_title = config["fields.roam.page.title"]
            f_roam_page_id = config["fields.roam.page.id"]
            f_roam_block_id = config["fields.roam.block.id"]
            f_roam_block_created = config["fields.roam.block.created"]
            f_roam_block_updated = config["fields.roam.block.updated"]

            if existing_note[f_text] != note.text:
                if existing_note[f_text] == existing_note[f_roam_text]:
                    # The note was updated on Roam, but hasn't been changed
                    # manually in Anki. Update it.
                    existing_note[f_text] = note.text
                    updated = True

            l = lambda x: "" if x == None else x

            if l(existing_note[f_roam_text]) != l(note.roam_text):
                updated = True
                existing_note[f_roam_text] = l(note.roam_text)

            if l(existing_note[f_roam_source]) != l(note.roam_source):
                updated = True
                existing_note[f_roam_source] = l(note.roam_source)

            if l(existing_note[f_roam_graph]) != l(note.roam_graph):
                updated = True
                existing_note[f_roam_graph] = l(note.roam_graph)

            if l(existing_note[f_roam_page_id]) != l(note.roam_page_id):
                updated = True
                existing_note[f_roam_page_id] = l(note.roam_page_id)

            if l(existing_note[f_roam_page_title]) != l(note.roam_page_title):
                updated = True
                existing_note[f_roam_page_title] = l(note.roam_page_title)

            if l(existing_note[f_roam_block_created]) != l(note.roam_block_created):
                updated = True
                existing_note[f_roam_block_created] = l(note.roam_block_created)

            if l(existing_note[f_roam_block_updated]) != l(note.roam_block_updated):
                updated = True
                existing_note[f_roam_block_updated] = l(note.roam_block_updated)

            existing_note.flush()
            return updated

        new_note = self._note(note, config)
        self.collection.addNote(new_note)
        return True

    def _setfield(self, note: AnkiNote, config: JsonData, field: str, data: Optional[str]):
        if data is not None:
            note[config[field]] = data


    def _note(self, anki_note: AnkiNote, config: JsonData) -> Note:
        note = Note(self.collection, self.model)

        self._setfield(note, config, "fields.text", anki_note.text)
        self._setfield(note, config, "fields.roam.text", anki_note.roam_text)
        self._setfield(note, config, "fields.roam.source", anki_note.roam_source)
        self._setfield(note, config, "fields.roam.graph", anki_note.roam_graph)
        self._setfield(note, config, "fields.roam.page.title", anki_note.roam_page_title)
        self._setfield(note, config, "fields.roam.page.id", anki_note.roam_page_id)
        self._setfield(note, config, "fields.roam.block.id", anki_note.roam_block_id)
        self._setfield(note, config, "fields.roam.block.created", anki_note.roam_block_created)
        self._setfield(note, config, "fields.roam.block.updated", anki_note.roam_block_updated)

        return note

    def get_block_ids(self) -> Iterable[str]:
        res = self.collection.db.all(
            'select id, flds from notes where mid = ?', self.model['id'])
        for (nid, fields) in res:
            yield splitFields(fields)[self.block_id_field_index], nid


@dataclass
class AnkiAddonData:
    anki_qt: AnkiQt

    def read_config(self) -> JsonData:
        return self.anki_qt.addonManager.getConfig(__name__)

@dataclass
class AnkiCollection:
    collection: _Collection

    def get_model_notes(self, config: JsonData) -> AnkiModelNotes:
        block_id_field = config['fields.roam.block.id']
        model = self._get_model(config['model.name'], config['deck.name'])
        field_names = self.collection.models.fieldNames(model)
        block_id_field_index = field_names.index(block_id_field)
        return AnkiModelNotes(self.collection, model, block_id_field_index, config)

    def _get_model(self, model_name: str, deck_name: Optional[str]) -> NoteType:
        model = deepcopy(self.collection.models.byName(model_name))
        self._set_deck_for_new_cards(model, deck_name)
        return model

    def _set_deck_for_new_cards(
        self, model: NoteType, deck_name: Optional[str],
    ) -> None:
        if deck_name:
            deck_id = self.collection.decks.id(deck_name, create=True)
            model['did'] = deck_id
