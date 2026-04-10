import os
from openai import OpenAI

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


# === 4. ВИДЕО ===
# видео только внутри контейнера
# def build_video():
#     os.system("""
#     ffmpeg -y -i assets/bg.mp4 -i voice.mp3 \
#     -c:v copy -c:a aac -shortest final.mp4
#     """)

# сохранение видео вне контейнера
def build_video():
    os.makedirs("output", exist_ok=True)

    os.system("""
    ffmpeg -y -i assets/bg.mp4 -i voice.mp3 \
    -c:v copy -c:a aac -shortest output/final.mp4
    """)


# === MAIN ===
def main():
    topic = generate_topic()
    print("Тема:", topic)

    script = generate_script(topic)
    print("Сценарий:", script)

    tts(script)
    build_video()

    print("Готово: final.mp4")


if __name__ == "__main__":
    main()