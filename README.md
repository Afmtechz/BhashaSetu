# Bhasha-Setu AI

> **Live classroom translation for multilingual learning**

Bhasha-Setu AI is a browser-based classroom prototype that helps a teacher
teach in English or Telugu while students listen and read in Hindi or Telugu.
It combines live speech recognition, translation, translated speech, subtitles,
and direct teacher video streaming in one lightweight demo.

No Android app, Flutter installation, database, or classroom account is
required.

---

## ✨ What the demo can do

### Teacher

- Start and stop a live lecture.
- Share microphone audio with Sarvam Saaras realtime STT.
- Share live camera video with students through WebRTC.
- View live original-language transcription.
- Mute or unmute the microphone.
- See the number and names of connected students.
- Receive student questions translated into English.
- Accept a named student's request to speak.

### Student

- Join with a name.
- Select a preferred language:
  - Hindi
  - Telugu
- Watch the teacher's live video.
- Read translated subtitles.
- Hear translated Bulbul speech automatically.
- Mute or unmute translated audio.
- Request permission to speak.
- Ask a question in the selected language.

### Supported classroom language paths

| Teacher speech | Student output |
|---|---|
| English | Hindi |
| English | Telugu |
| Telugu | Hindi |
| Telugu | Telugu |

For student questions:

```text
Student speaks Hindi or Telugu
        ↓
Sarvam Saaras realtime STT
        ↓
Sarvam Mayura translation
        ↓
English question shown to teacher
```

---

## 🎬 How it works

```text
┌─────────────────────┐
│  Teacher browser    │
│  microphone + video │
└──────────┬──────────┘
           │
           ├── WebSocket audio ──► Sarvam Saaras v3 realtime
           │                           │
           │                           ▼
           │                     Final sentence
           │                           │
           │                    Sarvam Mayura v1
           │                           │
           │                    Sarvam Bulbul v3
           │                           │
           │                           ▼
           │                 Subtitle + translated WAV
           │
           └── WebRTC video ───────────────► Student browser
```

The Python server handles speech and signaling. Teacher video is sent directly
to students using WebRTC; the server does not proxy or store video.

---

## 🧱 Project structure

```text
.
├── backend/
│   └── app/
│       ├── main.py              # FastAPI app factory
│       ├── config.py            # Environment variables and API constants
│       ├── hub.py               # In-memory classroom state
│       ├── routers/
│       │   ├── pages.py         # GET /, /health, class APIs
│       │   ├── teacher.py       # WS /ws/teacher
│       │   └── student.py       # WS /ws/student
│       └── services/
│           ├── sarvam.py        # Sarvam STT, translation, and TTS calls
│           └── pipeline.py      # Transcript and classroom message flow
├── static/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── main.py                      # Compatibility entrypoint
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔑 Sarvam configuration

Create an API key from the [Sarvam dashboard](https://dashboard.sarvam.ai).

Create a `.env` file beside `main.py`:

```env
SARVAM_API_KEY=your_sarvam_subscription_key
SARVAM_TTS_SPEAKER=shubh
PORT=8000
```

The API key is loaded only by the FastAPI backend. It is never placed in the
browser code or sent to students.

### Sarvam APIs used

| Capability | Current interface |
|---|---|
| Realtime speech-to-text | `wss://api.sarvam.ai/speech-to-text-realtime/ws` |
| STT model | `saaras:v3-realtime` |
| STT language mode | `language_code=auto` |
| STT audio format | Mono `linear16`, 16 kHz |
| Translation | `POST https://api.sarvam.ai/translate` |
| Translation model | `mayura:v1` |
| Text-to-speech | `POST https://api.sarvam.ai/text-to-speech` |
| TTS model | `bulbul:v3` |
| TTS output | Base64-encoded WAV |

---

## 🚀 Quick start

### 1. Open PowerShell

```powershell
cd "C:\Users\Sohan\OneDrive\Desktop\Test"
```

### 2. Install backend dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Create your environment file

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace the placeholder with your Sarvam API key.

### 4. Start the server

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Keep this terminal window open.

### 5. Open the website

On the same computer, open:

```text
http://127.0.0.1:8000
```

The backend also exposes a health check:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "sarvam_configured": "true"
}
```

## ☁️ Deploying with Vercel

Vercel serves the browser client, but its serverless functions do not support
long-lived WebSockets. The live Sarvam stream therefore must run on a
WebSocket-capable host such as Railway, Render, Fly.io, or a VM.

1. Deploy `main.py` with the commands below on the WebSocket host:

   ```text
   Build:  pip install -r requirements.txt
   Start:  uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
   ```

2. Set `SARVAM_API_KEY` and `SARVAM_TTS_SPEAKER` in that host's environment.
   Do not put the Sarvam key in Vercel or browser code.
3. Deploy this repository to Vercel with [`vercel.json`](./vercel.json).
4. Open the Vercel URL with the backend origin in the `backend` query
   parameter, for example:

   ```text
   https://your-app.vercel.app/?backend=https%3A%2F%2Fyour-api.example.com
   ```

The teacher clicks **Start lecture** to create a class and receives a short
class code. Students enter that code before joining. This prevents students
from accidentally joining a different active classroom.

---

## 🧪 Test with a teacher and a student

### Same computer

Open two browser tabs:

```text
Tab 1: Teacher
Tab 2: Student
```

#### Teacher tab

1. Select **Teacher**.
2. Click **Start lecture**.
3. Allow microphone and camera permissions.
4. Keep the tab open.

#### Student tab

1. Select **Student**.
2. Enter a student name.
3. Select Hindi or Telugu.
4. Click **Join classroom**.
5. Confirm that the teacher video appears.
6. Speak a complete sentence as the teacher.
7. Pause briefly so Saaras can detect the end of the sentence.

The student should receive:

- Teacher video
- Translated subtitle
- Translated audio

### Two devices on the same Wi-Fi

Find the computer's local IP address:

```powershell
ipconfig
```

Find the IPv4 address, for example:

```text
192.168.1.20
```

Open this URL on the second device:

```text
http://192.168.1.20:8000
```

The computer and the second device must be connected to the same Wi-Fi
network.

---

## 🔒 Recommended: use HTTPS for another device

Browsers often block microphone and camera access on ordinary local network
HTTP URLs. The simplest way to test across devices is an HTTPS tunnel.

Install [ngrok](https://ngrok.com/download), then run:

```powershell
ngrok http 8000
```

Open the generated HTTPS URL on both devices:

```text
https://your-subdomain.ngrok-free.app
```

The page automatically selects:

```text
HTTPS → secure WebSockets (wss://)
HTTP  → normal WebSockets (ws://)
```

---

## 🙋 Student speaking flow

1. Student enters a name and selects Hindi or Telugu.
2. Student clicks **Join classroom**.
3. Student clicks **Ask to speak**.
4. Teacher sees the student's name and request.
5. Teacher clicks **Allow**.
6. Student speaks in the selected language.
7. Sarvam transcribes and translates the question to English.
8. The teacher sees the student's original question and English translation.

The student microphone is not enabled for classroom speech until the teacher
accepts the request.

---

## 🔄 Sync and media behavior

### Video

Teacher video uses WebRTC with browser-to-browser media delivery. FastAPI
relays only:

- WebRTC offer
- WebRTC answer
- ICE candidates

The Python server does not store or proxy the camera stream.

### Subtitles and translated audio

Speech is processed sentence by sentence rather than token by token:

1. Sarvam detects a speech turn.
2. Saaras returns a final transcript.
3. Mayura translates the sentence.
4. Bulbul generates translated WAV audio.
5. The student receives the subtitle and audio together.

Each translated segment contains a `segment_id` so the subtitle, translation,
and audio can be associated with the same spoken sentence.

Because translation and speech synthesis require network processing, the video
remains live while subtitles and translated audio arrive shortly afterward.

---

## 🛠 Troubleshooting

### The page does not load

Make sure Uvicorn is running:

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Open the website through the server:

```text
http://127.0.0.1:8000
```

Do not double-click `static/index.html`.

### “Cannot connect to backend”

Check:

- The PowerShell window running Uvicorn is still open.
- The URL uses port `8000`.
- The second device uses the computer's correct IP address.
- Both devices are on the same network.
- HTTPS is used for microphone/camera access on another device.
- The browser is using the same website URL for Teacher and Student.

### Camera or microphone does not start

Check:

- Browser permission was allowed.
- The page is opened on `localhost` or HTTPS.
- Another application is not using the camera or microphone.
- The browser supports WebRTC and `getUserMedia`.

### Student video is blank

Check:

- The student joined after the teacher started the lecture.
- Camera permission was allowed on the teacher device.
- The student page was opened through the same HTTPS tunnel when using ngrok.
- The browser console does not show a WebRTC permission or ICE error.

### No translation arrives

Check:

- `http://127.0.0.1:8000/health` reports `"sarvam_configured": "true"`.
- The Sarvam API key is valid.
- The Sarvam account has available usage.
- The student joined before the teacher spoke.
- The teacher paused after speaking a complete sentence.

---

## ⚠️ Prototype limitations

This is intentionally a simple demo:

- One in-memory active classroom per Python process (restart ends the class).
- No authentication.
- No database or persistent classroom history.
- No Redis or horizontal scaling.
- No persistent classroom history or accounts.
- No reconnect recovery.
- Video depends on WebRTC network conditions.
- A public STUN server is used for peer discovery.
- Translation and TTS latency depends on browser, network, and API response time.

For production, the next steps would be secure authentication, classroom
session IDs, TURN servers, persistent state, rate limiting, observability, and
server-side media/session lifecycle management.

---

## 📄 License and security

Do not commit `.env` or expose your Sarvam API key in frontend code.

The included [.env.example](./.env.example) contains placeholders only.
