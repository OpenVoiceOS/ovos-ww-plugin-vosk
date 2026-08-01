## Description

Vosk wake word plugin for [OpenVoiceOS](https://github.com/OpenVoiceOS). It uses the
[Vosk](https://alphacephei.com/vosk/) speech recognizer to transcribe short audio
chunks and check the transcript against one or more wake word samples.

## Install

`pip install ovos-ww-plugin-vosk`

## Configuration

### Quick start

Add the following to the `hotwords` section in `mycroft.conf`.

```json
  "listener": {
    "wake_word": "hey_computer"
  },
  "hotwords": {
    "hey_computer": {
        "module": "ovos-ww-plugin-vosk",
        "listen": true
    }
  }
```

Replace `hey_computer` with your wake word. A model downloads automatically for the
configured language.

### Single keyword

Some wake words are hard to trigger, usually because the language model does not
include them. For example, `hey mycroft` is often transcribed as `hey microsoft`. By
default, this plugin checks for the wake word name, but you can configure the keyword
in a number of ways.

- `model_folder` - full path to a Vosk model. Optional; the plugin downloads one automatically.
- `lang` - language code for the model. Optional; uses the global value if not set. Only affects which model downloads.
- `debug` - if true, prints extra info, like the transcript contents.
- `rule` - how to compare the transcript against the samples. See the rules below.
- `time_between_checks` - the length in seconds between inferences. Must be between 0.2 and 3.
- `full_vocab` - use the full model vocabulary for transcription. If false (default), Vosk runs in keyword mode.
- `samples` - list of samples to match the rules against. Optional; defaults to the keyword name.

```json
  "listener": {
    "wake_word": "hey_computer"
  },
  "hotwords": {
    "hey_computer": {
        "module": "ovos-ww-plugin-vosk",
        "listen": true,
        "full_vocab": true,
        "rule": "equals",
        "debug": true,
        "samples": ["hey computer", "a computer", "hey computed"],
        "model_folder": "/home/user/Downloads/vosk-model-small-en-us-0.4",
        "time_between_checks": 0.6
    }
  }
```

#### Keyword rules

You can define different rules to trigger a wake word.

- `contains` - the transcript contains any of the samples.
- `equals` - the transcript exactly matches any of the samples.
- `starts` - the transcript starts with any of the samples.
- `ends` - the transcript ends with any of the samples.
- `fuzzy` - fuzzy match the transcript against the samples.

Enable the `debug` flag and check the logs to see what the plugin transcribes. Use
this to tune the rule and samples.

Each wake word must fit in 3 seconds, the length of audio the model parses at a time.

`time_between_checks` controls how often the plugin checks the buffered audio.
Lower values run more checks and use more CPU. Higher values check less often and may
miss short wake words. The default is 1.0.

Set `full_vocab` to transcribe all known words before applying the detection rules. By
default this is false, and the plugin only looks for the wake word samples. Depending
on the wake word, this may raise or lower accuracy.

### Multiple keywords

A single model per language can check for multiple keywords at once. For example, to
replace the default wake words:

```json
  "hotwords": {
    "hey mycroft": {"active": false},
    "wake up": {"active": false},
    "hey xxx": {
        "module": "ovos-ww-plugin-vosk-multi",
        "listen": true,
        "wakeup": true,
        "keywords": {
           "hey mycroft": {"samples": ["hey mycroft", "hey microsoft", "hey minecraft"], "rule": "fuzzy"},
           "wake up": {"wakeup": true}
        }
    }
```

You can load any number of languages side by side.

```json
  "hotwords": {
    "hey_xxx": {
        "module": "ovos-ww-plugin-vosk-multi",
        "listen": true,
        "full_vocab": false,
        "keywords": {
           "hey mycroft": {"samples": ["hey mycroft", "hey microsoft", "hey minecraft"], "rule": "fuzzy"},
           "hey neon": {},
           "hey computer": {},
           "hey jarvis": {},
           "computador": {"lang": "pt"},
           "jarbas": {"lang": "pt"}
        }
    }
```

## Related projects

- [OpenVoiceOS/ovos-plugin-manager](https://github.com/OpenVoiceOS/ovos-plugin-manager) - loads and manages OVOS plugins, including wake word engines like this one.
- [OpenVoiceOS/ovos-dinkum-listener](https://github.com/OpenVoiceOS/ovos-dinkum-listener) - the OVOS listener service that runs wake word plugins against microphone audio.

## License

Apache-2.0
