import os
import subprocess
from openai import OpenAI
from faster_whisper import WhisperModel

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# === 1. ТЕМА ===
def generate_topic():
    r = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{
            "role": "user",
            "content": "Придумай вирусную тему для YouTube Shorts про технологии"
        }]
    )
    return r.choices[0].message.content.strip()


# === 2. СЦЕНАРИЙ ===
def generate_script(topic):
    r = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{
            "role": "user",
            "content": f"""
            Напиши короткий текст (до 80 слов) для YouTube Shorts.
            Сделай мощный хук в начале.
            Без воды.
            Тема: {topic}
            """
        }]
    )
    return r.choices[0].message.content.strip()


# === 3. ОЗВУЧКА (OpenAI TTS) ===
def tts(text):
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text
    )

    with open("voice.mp3", "wb") as f:
        f.write(response.content)

# === 3. СУБТИТРЫ (WHISPER) ===
def generate_subtitles():
    model = WhisperModel("base", compute_type="int8")

    segments, info = model.transcribe("voice.mp3")

    with open("subtitles.srt", "w") as f:
        for i, segment in enumerate(segments, start=1):
            start = format_time(segment.start)
            end = format_time(segment.end)
            text = segment.text.strip()

            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)

    return f"{h:02}:{m:02}:{s:02},{ms:03}"

# === 4. ВИДЕО ===
# видео без субтитров
# def build_video():
#     os.makedirs("output", exist_ok=True)
#
#     os.system("""
#     ffmpeg -y \
#     -i assets/bg.mp4 \
#     -i voice.mp3 \
#     -map 0:v:0 \
#     -map 1:a:0 \
#     -c:v copy \
#     -c:a aac \
#     -shortest \
#     output/final.mp4
#     """)

# видео с субтитрами
def build_video():
    import os
    os.makedirs("output", exist_ok=True)

    os.system("""
    ffmpeg -y \
    -i assets/bg.mp4 \
    -i voice.mp3 \
    -vf "subtitles=subtitles.srt:force_style='FontSize=24,PrimaryColour=&Hffffff&'" \
    -map 0:v:0 \
    -map 1:a:0 \
    -c:v libx264 \
    -c:a aac \
    -shortest \
    output/final.mp4
    """)


# === MAIN ===
def main():
    topic = generate_topic()
    print("Тема:", topic)

    script = generate_script(topic)
    print("Сценарий:", script)

    tts(script)
    generate_subtitles()
    build_video()

    print("Готово: output/final.mp4")


if __name__ == "__main__":
    main()