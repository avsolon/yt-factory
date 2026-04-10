import requests
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# === НАСТРОЙКИ ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")

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
    return r.choices[0].message.content


# === 2. СЦЕНАРИЙ ===
def generate_script(topic):
    r = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{
            "role": "user",
            "content": f"Напиши короткий текст (до 80 слов) с мощным хуком. Тема: {topic}"
        }]
    )
    return r.choices[0].message.content


# === 3. ОЗВУЧКА ===
def tts(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2"
    }

    response = requests.post(url, json=data, headers=headers)

    with open("voice.mp3", "wb") as f:
        f.write(response.content)


# === 4. ВИДЕО ===
def build_video():
    os.system("""
    ffmpeg -y -i assets/bg.mp4 -i voice.mp3 \
    -c:v copy -c:a aac -shortest final.mp4
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