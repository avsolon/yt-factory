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


def tts(text):
    text = text.strip()
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text
    ) as response:
        response.stream_to_file("voice.mp3")


# =======================
# SUBTITLES
# =======================

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def generate_subtitles():
    print("Генерация субтитров...")
    model = WhisperModel("base", compute_type="int8")

    segments, _ = model.transcribe("voice.mp3")

    with open("subtitles.srt", "w") as f:
        for i, segment in enumerate(segments, start=1):
            f.write(f"{i}\n")
            f.write(f"{format_time(segment.start)} --> {format_time(segment.end)}\n")
            f.write(f"{segment.text.strip()}\n\n")


# ======================
# VIDEO
# ======================
def build_video(use_subtitles=True):
    os.makedirs("output", exist_ok=True)

    audio_duration = validate_audio_duration("voice.mp3")

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", "assets/bg.mp4",
        "-i", "voice.mp3",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac",
        "-t", str(audio_duration),
        "-shortest",
    ]

    if use_subtitles:
        cmd += ["-vf", "subtitles=subtitles.srt"]

    cmd += ["output/final.mp4"]

    subprocess.run(cmd, check=True)

def get_audio_duration(file):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        file
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if not result.stdout:
        raise ValueError("ffprobe returned empty output")

    data = json.loads(result.stdout)
    return float(data["format"]["duration"])

def validate_audio_duration(path):
    duration = get_audio_duration(path)

    print(f"🎧 Audio duration: {duration:.2f}s")

    if duration > MAX_DURATION:
        raise ValueError(f"❌ Слишком длинное видео: {duration:.1f}s (max {MAX_DURATION}s)")

    if duration < MIN_DURATION:
        print("⚠️ Слишком коротко, но продолжаем")

    return duration

def run_ai_pipeline():
    topic = generate_topic()
    print("🧠 Topic:", topic)

    script = generate_script(topic)
    print("✍️ Script:", script)

    tts(script)

    duration = validate_audio_duration("voice.mp3")

    build_video(use_subtitles=True)

    print("✅ DONE")

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