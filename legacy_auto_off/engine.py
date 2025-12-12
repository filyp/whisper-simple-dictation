import sys
import numpy as np
from flask import Flask, request, jsonify
from faster_whisper import WhisperModel

app = Flask(__name__)

model_name = sys.argv[1]
print(f"Using model: {model_name}")

model = WhisperModel(model_name, device="cuda", compute_type="float16")


def get_text_local(audio, context=None):
    segments, info = model.transcribe(audio, beam_size=5, language="en", initial_prompt=context)
    segments = list(segments)
    text = " ".join([segment.text.strip() for segment in segments])
    return text


@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.get_json()
    if "audio" not in data:
        return jsonify({"error": "No audio data provided"}), 400
    
    context = data.get("context", None)

    try:
        audio_array = np.array(data["audio"])
        text = get_text_local(audio_array, context)
        return jsonify({"text": text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5900, use_reloader=False)
