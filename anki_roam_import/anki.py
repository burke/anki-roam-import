import os
from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable, Optional

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

    def add_note(self, anki_note: AnkiNote) -> None:
        note = self._note(anki_note)
        self.collection.addNote(note)

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

    def get_notes(self) -> Iterable[str]:
        note_fields = self.collection.db.list(
            'select flds from notes where mid = ?', self.model['id'])
        for fields in note_fields:
            yield splitFields(fields)[self.content_field_index]


@dataclass
class AnkiAddonData:
    anki_qt: AnkiQt

    def read_config(self) -> JsonData:
        return self.anki_qt.addonManager.getConfig(__name__)

    def user_files_path(self) -> str:
        module_name = __name__.split('.')[0]
        addons_directory = self.anki_qt.addonManager.addonsFolder(module_name)
        user_files_path = os.path.join(addons_directory, 'user_files')
        os.makedirs(user_files_path, exist_ok=True)
        return user_files_path


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
