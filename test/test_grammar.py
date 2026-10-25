"""The grammar ModelContainer hands to Kaldi holds each sample as Vosk reads it."""
import json

import ovos_ww_plugin_vosk
from ovos_ww_plugin_vosk import ModelContainer


def test_accented_samples_reach_the_grammar_as_written(monkeypatch, tmp_path):
    grammars = []
    monkeypatch.setattr(ovos_ww_plugin_vosk, "KaldiModel", lambda path: path)
    monkeypatch.setattr(ovos_ww_plugin_vosk, "KaldiRecognizer",
                        lambda model, rate, *grammar: grammars.append(grammar))
    ModelContainer(["joão", "réveille-toi"]).get_model(str(tmp_path))
    # Vosk matches the grammar text against its vocabulary byte for byte:
    # a \u escape is a word it does not know, so the sample could never match
    assert grammars == [('["joão", "réveille-toi", "[unk]"]',)]
    assert json.loads(grammars[0][0]) == ["joão", "réveille-toi", "[unk]"]
