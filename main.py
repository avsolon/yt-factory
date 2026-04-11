import os
import json
import argparse
import subprocess
from openai import OpenAI
from faster_whisper import WhisperModel

MAX_DURATION = 45
MIN_DURATION = 25
MAX_WORDS = 120

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =======================
# CLI
# =======================
parser = argparse.ArgumentParser()

parser.add_argument("--mode", choices=["ai", "user"], default="ai")
parser.add_argument("--text", type=str, help="User text")
parser.add_argument("--no-subtitles", action="store_true")
parser.add_argument("--audio-only", action="store_true")

args = parser.parse_args()

# =======================
# GENERATION
# =======================

def generate_topic():
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Придумай тему для вирусного видео"}]
    )
    return response.choices[0].message.content


def generate_script(topic):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"""
                Ты сценарист YouTube Shorts.
                Сделай видео на 25–40 секунд.              
                Тема: {topic}           
                ОГРАНИЧЕНИЯ:
                - максимум {MAX_WORDS} слов
                - короткие фразы
                - динамичный стиль
                - без воды
                - это текст для озвучки                
                ФОРМАТ:
                Один связный текст без пунктов
                """
            }
        ]
    )
    return response.choices[0].message.content.strip()


def tts(text, output="voice.mp3"):
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text
    ) as response:
        response.stream_to_file(output)

    return output


# =======================
# SUBTITLES
# =======================

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def generate_subtitles(audio_file):
    print("📝 Генерация субтитров...")
    model = WhisperModel("tiny", compute_type="int8")

    segments, _ = model.transcribe(audio_file)

    with open("subtitles.srt", "w") as f:
        for i, segment in enumerate(segments, start=1):
            f.write(f"{i}\n")
            f.write(f"{format_time(segment.start)} --> {format_time(segment.end)}\n")
            f.write(f"{segment.text.strip()}\n\n")

    if not os.path.exists("subtitles.srt"):
        raise Exception("❌ subtitles.srt не создан")


# =======================
# AUDIO
# =======================

def get_audio_duration(file):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        file
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    return float(data["format"]["duration"])

def validate_audio_duration(path):
    duration = get_audio_duration(path)

    print(f"🎧 Audio duration: {duration:.2f}s")

    if duration > MAX_DURATION:
        print(f"⚠️ Слишком длинно ({duration:.1f}s) → обрезаем до {MAX_DURATION}s")

        trimmed = "voice_cut.mp3"

        subprocess.run([
            "ffmpeg", "-y",
            "-i", path,
            "-t", str(MAX_DURATION),
            trimmed
        ], check=True)

        return trimmed   # 👈 ТОЛЬКО ФАЙЛ
    return path

# ======================
# VIDEO
# ======================
def build_video(audio_file="voice.mp3", use_subtitles=True):
    os.makedirs("output", exist_ok=True)

    if use_subtitles and not os.path.exists("subtitles.srt"):
        print("⚠️ subtitles.srt не найден → отключаем субтитры")
        use_subtitles = False

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", "assets/bg.mp4",
        "-i", audio_file,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "ultrafast", #medium
        "-crf", "28", #20
        "-c:a", "aac",
    ]

    vf_filters = []
    if use_subtitles:
        vf_filters.append(f"subtitles={os.path.abspath('subtitles.srt')}")
    if vf_filters:
        cmd += ["-vf", ",".join(vf_filters)]
    cmd += ["-shortest", "output/final.mp4"]
    print("🎬 FFmpeg cmd:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def run_ai_pipeline():
    topic = generate_topic()
    script = generate_script(topic)

    audio_file = tts(script)
    audio_file = validate_audio_duration(audio_file)

    try:
        generate_subtitles(audio_file)
        use_subs = True
    except Exception as e:
        print("⚠️ Ошибка субтитров:", e)
        use_subs = False
    build_video(audio_file, use_subtitles=use_subs)
    print("DONE")

# =======================
# MAIN
# =======================

def main():
    # выбор текста
    if args.mode == "ai":
        topic = generate_topic()
        print("Тема:", topic)

        script = generate_script(topic)
    else:
        if not args.text:
            raise Exception("Нужно передать --text")
        script = args.text

    print("Сценарий:", script)

    # озвучка
    tts(script)

    # если только аудио
    if args.audio_only:
        print("Готово: voice.mp3")
        return

    # субтитры
    if not args.no_subtitles:
        generate_subtitles()

    # видео
    build_video(use_subtitles=not args.no_subtitles)

    print("Готово: output/final.mp4")


if __name__ == "__main__":
    if args.mode == "ai":
        run_ai_pipeline()

    elif args.mode == "user":
        script = args.text

        tts(script)
        validate_audio_duration("voice.mp3")
        build_video(use_subtitles=True)