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
from os.path import isdir
import json
from vosk import Model as KaldiModel, KaldiRecognizer
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.hotwords import HotWordEngine


class VoskWakeWordPlugin(HotWordEngine):
    """Vosk Wake Word"""
    # Hard coded values in mycroft/client/speech/mic.py
    SEC_BETWEEN_WW_CHECKS = 0.2
    MAX_EXPECTED_DURATION = 3  # seconds of data chunks received at a time

    def __init__(self, hotword="hey mycroft", config=None, lang="en-us"):
        config = config or {}
        super(VoskWakeWordPlugin, self).__init__(hotword, config, lang)
        model_path = self.config.get("model_folder")
        if not model_path or not isdir(model_path):
            LOG.error("You need to provide a valid model folder")
            LOG.info(
                "download a model from https://alphacephei.com/vosk/models")
            raise FileNotFoundError
        self.model = KaldiModel(model_path)
        self.kaldi = KaldiRecognizer(self.model, 16000)
        default_sample = [hotword.replace("_", " ").replace("-", " ")]
        self.samples = self.config.get("samples", default_sample)
        self.rule = self.config.get("rule", "contains")
        self.debug = self.config.get("debug", False)
        self.time_between_checks = \
            min(self.config.get("time_between_checks", 0.5), 3)
        self.expected_duration = self.MAX_EXPECTED_DURATION
        self._counter = 0

    def found_wake_word(self, frame_data):
        """ frame data contains audio data that needs to be checked for a wake
        word, you can process audio here or just return a result
        previously handled in update method """
        self._counter += self.SEC_BETWEEN_WW_CHECKS
        if self._counter < self.time_between_checks:
            return False
        self._counter = 0
        self.kaldi.AcceptWaveform(frame_data)
        res = self.kaldi.FinalResult()
        transcript = json.loads(res)["text"].lower().strip()
        if not transcript:
            return False
        if self.debug:
            LOG.info("TRANSCRIPT: " + transcript)
        for s in self.samples:
            s = s.lower().strip()
            if self.rule == "contains":
                if s in transcript:
                    return True
            elif self.rule == "equals":
                if s == transcript:
                    return True
            elif self.rule == "starts":
                if transcript.startswith(s):
                    return True
            elif self.rule == "ends":
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
