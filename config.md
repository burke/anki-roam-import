`model_name` is the name of the model to use for imported notes. Defaults to "Cloze".

`content_field` is the name of the field in which to put the content of the
note. Defaults to "Text".

`roam_content_field` is the name of the field in which to copy the note on import. Later on, this is
used if the note text has changed to determine whether it was changed in Roam or in Anki. Defaults
to "RoamText".

`source_field` is the name of the field in which to put the source of the note. Defaults to
"Source".

`block_id_field` is the name of the field in which to put the Roam Block ID of the note. Defaults to
"BlockID".

`graph_field` is the name of the field in which to record the name of the graph from which the block
was imported. Defaults to "Graph".

`graph_name` is the name of the graph that will be imported. This is saved to imported notes using
`graph_field`.

`deck_name` is the name of the deck in which to put the imported cards. Defaults to null, which
means use the default deck.
