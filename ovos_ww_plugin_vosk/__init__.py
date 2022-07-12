# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import json
from os.path import join, exists
import enum
from ovos_plugin_manager.templates.hotwords import HotWordEngine
from ovos_skill_installer import download_extract_zip, download_extract_tar
from ovos_utils.log import LOG
from ovos_utils.parse import fuzzy_match, MatchStrategy
from ovos_utils.xdg_utils import xdg_data_home
from speech_recognition import AudioData
from vosk import Model as KaldiModel, KaldiRecognizer


class MatchRule(str, enum.Enum):
    CONTAINS = "contains"
    EQUALS = "equals"
    STARTS = "starts"
    ENDS = "ends"
    FUZZY = "fuzzy"
    TOKEN_SET_RATIO = "token_set_ratio"
    TOKEN_SORT_RATIO = "token_sort_ratio"
    PARTIAL_TOKEN_SET_RATIO = "partial_token_set_ratio"
    PARTIAL_TOKEN_SORT_RATIO = "partial_token_sort_ratio"


class ModelContainer:
    UNK = "[unk]"
    engines = {}
    models = {}

    def __init__(self, samples=None, full_vocab=False):
        if not full_vocab and not samples:
            full_vocab = True
        samples = samples or []
        if self.UNK not in samples:
            samples.append(self.UNK)
        self.samples = samples
        self.full_vocab = full_vocab

    def get_engine(self, lang):
        lang = lang.split("-")[0].lower()
        self.load_language(lang)
        return self.engines[lang]

    def get_partial_transcription(self, lang):
        engine = self.get_engine(lang)
        res = engine.PartialResult()
        return json.loads(res)["partial"]

    def get_final_transcription(self, lang):
        engine = self.get_engine(lang)
        res = engine.FinalResult()
        return json.loads(res)["text"]

    def process_audio(self, audio, lang):
        engine = self.get_engine(lang)
        if isinstance(audio, AudioData):
            audio = audio.get_wav_data()
        return engine.AcceptWaveform(audio)

    def load_model(self, model_path, lang):
        lang = lang.split("-")[0].lower()
        self.models[lang] = model_path
        if model_path:
            if self.full_vocab:
                model = KaldiRecognizer(KaldiModel(model_path), 16000)
            else:
                model = KaldiRecognizer(KaldiModel(model_path), 16000,
                                        json.dumps(self.samples))
            self.engines[lang] = model
        else:
            raise FileNotFoundError

    def load_language(self, lang):
        lang = lang.split("-")[0].lower()
        if lang in self.engines:
            return
        model_path = self.download_language(lang)
        self.load_model(model_path, lang)

    def unload_language(self, lang):
        if lang in self.engines:
            del self.engines[lang]
            self.engines.pop(lang)

    @staticmethod
    def download_language(lang):
        lang = lang.split("-")[0].lower()
        model_path = ModelContainer.lang2modelurl(lang)
        if model_path and model_path.startswith("http"):
            model_path = ModelContainer.download_model(model_path)
        return model_path

    @staticmethod
    def download_model(url):
        folder = join(xdg_data_home(), 'vosk')
        name = url.split("/")[-1].split(".")[0]
        model_path = join(folder, name)
        if not exists(model_path):
            LOG.info(f"Downloading model for vosk {url}")
            LOG.info("this might take a while")
            if url.endswith(".zip"):
                download_extract_zip(url, folder=folder, skill_folder_name=name)
            else:
                download_extract_tar(url, folder=folder, skill_folder_name=name)
            LOG.info(f"Model downloaded to {model_path}")

        return model_path

    @staticmethod
    def lang2modelurl(lang, small=True):
        lang2url = {
            "en": "http://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
            "en-in": "http://alphacephei.com/vosk/models/vosk-model-small-en-in-0.4.zip",
            "cn": "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.3.zip",
            "ru": "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.15.zip",
            "fr": "https://alphacephei.com/vosk/models/vosk-model-small-fr-pguyot-0.3.zip",
            "de": "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip",
            "es": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.3.zip",
            "pt": "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip",
            "gr": "https://alphacephei.com/vosk/models/vosk-model-el-gr-0.7.zip",
            "tr": "https://alphacephei.com/vosk/models/vosk-model-small-tr-0.3.zip",
            "vn": "https://alphacephei.com/vosk/models/vosk-model-small-vn-0.3.zip",
            "it": "https://alphacephei.com/vosk/models/vosk-model-small-it-0.4.zip",
            "nl": "https://alphacephei.com/vosk/models/vosk-model-nl-spraakherkenning-0.6-lgraph.zip",
            "ca": "https://alphacephei.com/vosk/models/vosk-model-small-ca-0.4.zip",
            "ar": "https://alphacephei.com/vosk/models/vosk-model-ar-mgb2-0.4.zip",
            "fa": "https://alphacephei.com/vosk/models/vosk-model-small-fa-0.5.zip",
            "tl": "https://alphacephei.com/vosk/models/vosk-model-tl-ph-generic-0.6.zip"
        }
        biglang2url = {
            "en": "https://alphacephei.com/vosk/models/vosk-model-en-us-aspire-0.2.zip",
            "en-in": "http://alphacephei.com/vosk/models/vosk-model-en-in-0.4.zip",
            "cn": "https://alphacephei.com/vosk/models/vosk-model-cn-0.1.zip",
            "ru": "https://alphacephei.com/vosk/models/vosk-model-ru-0.10.zip",
            "fr": "https://github.com/pguyot/zamia-speech/releases/download/20190930/kaldi-generic-fr-tdnn_f-r20191016.tar.xz",
            "de": "https://alphacephei.com/vosk/models/vosk-model-de-0.6.zip",
            "nl": "https://alphacephei.com/vosk/models/vosk-model-nl-spraakherkenning-0.6.zip",
            "fa": "https://alphacephei.com/vosk/models/vosk-model-fa-0.5.zip"

        }
        if not small:
            lang2url.update(biglang2url)
        lang = lang.lower()
        if lang in lang2url:
            return lang2url[lang]
        lang = lang.split("-")[0]
        return lang2url.get(lang)


class VoskWakeWordPlugin(HotWordEngine):
    """Vosk Wake Word"""
    # Hard coded values in mycroft/client/speech/mic.py
    SEC_BETWEEN_WW_CHECKS = 0.2
    MAX_EXPECTED_DURATION = 3  # seconds of data chunks received at a time

    def __init__(self, hotword="hey mycroft", config=None, lang="en-us"):
        config = config or {}
        super(VoskWakeWordPlugin, self).__init__(hotword, config, lang)
        # model_folder for backwards compat
        model_path = self.config.get("model") or self.config.get("model_folder")
        default_sample = [hotword.replace("_", " ").replace("-", " ")]
        self.full_vocab = self.config.get("full_vocab", False)
        self.samples = self.config.get("samples", default_sample)
        self.rule = self.config.get("rule", MatchRule.EQUALS)
        self.thresh = self.config.get("threshold", 0.75)
        self.debug = self.config.get("debug", False)
        self.time_between_checks = \
            min(self.config.get("time_between_checks", 0.5), 3)
        self.expected_duration = self.MAX_EXPECTED_DURATION
        self._counter = 0

        self.model = ModelContainer(self.samples, self.full_vocab)
        if model_path:
            if model_path.startswith("http"):
                model_path = ModelContainer.download_model(model_path)
            self.model.load_model(model_path, self.lang)
        else:
            self.model.load_language(self.lang)

    def found_wake_word(self, frame_data):
        """ frame data contains audio data that needs to be checked for a wake
        word, you can process audio here or just return a result
        previously handled in update method """
        self._counter += self.SEC_BETWEEN_WW_CHECKS
        if self._counter < self.time_between_checks:
            return False
        self._counter = 0
        self.model.process_audio(frame_data, self.lang)
        transcript = self.model.get_final_transcription(self.lang)
        if not transcript or transcript == self.model.UNK:
            return False
        if self.debug:
            LOG.info("TRANSCRIPT: " + transcript)
        for s in self.samples:
            s = s.lower().strip()
            if self.rule == MatchRule.FUZZY:
                _, score = fuzzy_match(s, transcript)
                if score >= self.thresh:
                    return True
            elif self.rule == MatchRule.TOKEN_SORT_RATIO:
                _, score = fuzzy_match(s, transcript,
                                       strategy=MatchStrategy.TOKEN_SORT_RATIO)
                if score >= self.thresh:
                    return True
            elif self.rule == MatchRule.TOKEN_SET_RATIO:
                _, score = fuzzy_match(s, transcript,
                                       strategy=MatchStrategy.TOKEN_SET_RATIO)
                if score >= self.thresh:
                    return True
            elif self.rule == MatchRule.PARTIAL_TOKEN_SORT_RATIO:
                _, score = fuzzy_match(s, transcript,
                                       strategy=MatchStrategy.PARTIAL_TOKEN_SORT_RATIO)
                if score >= self.thresh:
                    return True
            elif self.rule == MatchRule.PARTIAL_TOKEN_SET_RATIO:
                _, score = fuzzy_match(s, transcript,
                                       strategy=MatchStrategy.PARTIAL_TOKEN_SET_RATIO)
                if score >= self.thresh:
                    return True
            elif self.rule == MatchRule.CONTAINS:
                if s in transcript:
                    return True
            elif self.rule == MatchRule.EQUALS:
                if s == transcript:
                    return True
            elif self.rule == MatchRule.STARTS:
                if transcript.startswith(s):
                    return True
            elif self.rule == MatchRule.ENDS:
                if transcript.endswith(s):
                    return True
        return False

    def update(self, chunk):
        """ In here you have access to live audio chunks, allows for
        streaming predictions, result still need to be returned in
        found_wake_word method """

    def stop(self):
        """ Perform any actions needed to shut down the hot word engine.

            This may include things such as unload loaded data or shutdown
            external processes.
        """
