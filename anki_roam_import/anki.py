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
    content_field_index: int
    source_field_index: Optional[int]
    block_id_field_index: Optional[int]
    graph_field_index: Optional[int]
    roam_text_field_index: Optional[int]

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

        new_note = self._note(note)
        self.collection.addNote(new_note)
        return True


    def _note(self, anki_note: AnkiNote) -> Note:
        note = Note(self.collection, self.model)
        note.fields[self.text_field_index] = anki_note.text
        if self.source_field_index is not None:
            note.fields[self.source_field_index] = anki_note.source
        if self.block_id_field_index is not None:
            note.fields[self.block_id_field_index] = anki_note.roam_block_id
        if self.graph_field_index is not None:
            note.fields[self.graph_field_index] = anki_note.graph
        if self.roam_text_field_index is not None:
            note.fields[self.roam_text_field_index] = anki_note.roam_text
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

    def get_model_notes(
        self,
        model_name: str,
        content_field: str,
        source_field: Optional[str],
        block_id_field: Optional[str],
        graph_field: Optional[str],
        roam_text_field: Optional[str],
        deck_name: Optional[str],
    ) -> AnkiModelNotes:
        model = self._get_model(model_name, deck_name)

        field_names = self.collection.models.fieldNames(model)
        content_field_index = field_names.index(content_field)

        if source_field is not None:
            source_field_index = field_names.index(source_field)
        else:
            source_field_index = None

        if block_id_field is not None:
            block_id_field_index = field_names.index(block_id_field)
        else:
            block_id_field_index = None

        if graph_field is not None:
            graph_field_index = field_names.index(graph_field)
        else:
            graph_field_index = None

        if roam_text_field is not None:
            roam_text_field_index = field_names.index(roam_text_field)
        else:
            roam_text_field_index = None

        return AnkiModelNotes(
            self.collection, model, content_field_index, source_field_index,
            block_id_field_index, graph_field_index, roam_text_field_index)

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
