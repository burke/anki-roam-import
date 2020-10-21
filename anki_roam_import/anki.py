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
    roam_content_field_index: Optional[int]

    # return: was new note created?
    # TODO(burke) could do tri-state here: NEW, UPDATE, NONE
    def add_or_update_note(self, note: AnkiNote, existing_block_ids: Dict[str, int]) -> bool:
        if note.block_id in existing_block_ids:
            note_id = existing_block_ids[note.block_id]
            existing_note = self.collection.getNote(note_id)
            updated = False

            if existing_note["Text"] != note.content:
                if existing_note["Text"] == existing_note["RoamText"]:
                    # The note was updated on Roam, but hasn't been changed
                    # manually in Anki. Update it.
                    existing_note["Text"] = note.content
                    updated = True

            if existing_note["Graph"] != note.graph:
                updated = True
                existing_note["Graph"] = note.graph

            if existing_note["RoamText"] != note.roam_content:
                updated = True
                existing_note["RoamText"] = note.roam_content

            if existing_note["Source"] != note.source:
                updated = True
                existing_note["Source"] = note.source

            existing_note.flush()
            return updated

        new_note = self._note(note)
        self.collection.addNote(new_note)
        return True


    def _note(self, anki_note: AnkiNote) -> Note:
        note = Note(self.collection, self.model)
        note.fields[self.content_field_index] = anki_note.content
        if self.source_field_index is not None:
            note.fields[self.source_field_index] = anki_note.source
        if self.block_id_field_index is not None:
            note.fields[self.block_id_field_index] = anki_note.block_id
        if self.graph_field_index is not None:
            note.fields[self.graph_field_index] = anki_note.graph
        if self.roam_content_field_index is not None:
            note.fields[self.roam_content_field_index] = anki_note.roam_content
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
        roam_content_field: Optional[str],
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

        if roam_content_field is not None:
            roam_content_field_index = field_names.index(roam_content_field)
        else:
            roam_content_field_index = None

        return AnkiModelNotes(
            self.collection, model, content_field_index, source_field_index,
            block_id_field_index, graph_field_index, roam_content_field_index)

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
