UA-Speech (Illinois) – Setup and run

Your data path: D:\research\data\UASpeech
Audio folder used: audio\original (or normalized / noisereduce if original has no WAVs)

If you see "0 (path, word) pairs" for all speakers, the script could not find WAV files.
- Check that D:\research\data\UASpeech\audio\original (or normalized or noisereduce) contains .wav files named like M16_B1_CW28_M7.wav.
- Then run the setup again (see commands below).

Commands to run (on your PC, in PowerShell or cmd):

1) Setup (parse MLF, build vocab, copy WAVs into sample_audio):
   cd "C:\Users\Ashwin Raj\PycharmProjects\ResearchProto\speech-adaptation-demo"
   python scripts/uaspeech_setup.py --uaspeech_root "D:\research\data\UASpeech" --sample_audio_dir "sample_audio" --copy_max 50

   To also build pseudo-sentences (optional):
   python scripts/uaspeech_setup.py --uaspeech_root "D:\research\data\UASpeech" --sample_audio_dir "sample_audio" --copy_max 50

   (Remove --skip_pseudo if you want pseudo-sentences; the script runs build_pseudo_sentences.py by default.)

2) Start the app:
   cd "C:\Users\Ashwin Raj\PycharmProjects\ResearchProto\speech-adaptation-demo"
   python app_phase2.py

3) In the app:
   - Create a profile (e.g. Illinois_M16).
   - Demo tab: choose a file from "Built-in Demo Audio" (files from sample_audio/uaspeech_<ID>/).
   - Open uaspeech_setup/uaspeech_<ID>_vocab.txt and paste its contents into "Custom Vocabulary".
   - For "Ground Truth": open uaspeech_setup/uaspeech_<ID>_basename_to_word.txt and look up the word for the selected file (first column = filename, second = word).
   - Click "Run Pipeline". Use Continual Learning to submit corrections when ASR is wrong.

See HOW_TO_RUN_UASPEECH.txt in this folder for full steps.
