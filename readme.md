## Description
Mycroft wake word plugin for [Vosk](https://alphacephei.com/vosk/)

The "plugins" are pip install-able modules that provide new engines for mycroft

more info in the [docs](https://mycroft-ai.gitbook.io/docs/mycroft-technologies/mycroft-core/plugins)

## Install

`mycroft-pip install jarbas-wake-word-plugin-vosk`

You can download official models from [alphacephei](https://alphacephei.com/vosk/models)

Models for Iberian Languages can be found [here](https://github.com/JarbasIberianLanguageResources/iberian-vosk) 

Using a small model is HIGHLY recommended

## Configuration

Add the following to your hotwords section in mycroft.conf 

```json
 "listener": {
      "wake_word": "hey_computer"
 },
  "hotwords": {
    "hey_computer": {
        "module": "vosk_ww_plug",
        "model_folder": "path/to/model/folder"
    }
  }
```

### Advanced config

Some wake words are hard to trigger, usually if missing from the language model, 
eg, `hey mycroft` is usually transcribed as `hey microsoft`, 
by default this plugin will check for the wake word name, but this can be overrided with a list of samples

TIP: enable `debug` flag and check logs for what is being transcribed, then finetune the rule and samples

You can define different rules to trigger a wake word

- `contains` - if the transcript contains any of provided samples 
- `equals` - if the transcript exactly matches any of provided samples 
- `starts` - if the transcript starts with any of provided samples 
- `ends` - if the transcript ends with any of provided samples 

Each wake word must fit in 3 seconds, which is the length of audio the model parses at a time

You can try to improve performance by tweaking `time_between_checks`, this is the length in seconds between inferences, must be between 0.2 and 3

Lower values will decrease performance, higher values will decrease accuracy, default value is 0.5

```json
 "listener": {
      "wake_word": "hey_computer"
 },
  "hotwords": {
    "hey_computer": {
        "module": "vosk_ww_plug",
        "rule": "equals",
        "debug": false,
        "samples": ["hey computer", "a computer", "hey computed"],
        "model_folder": "/home/user/Downloads/vosk-model-small-en-us-0.4",
        "time_between_checks": 0.6
    }
  }
```