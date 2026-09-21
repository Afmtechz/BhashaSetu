# Bhasha-Setu AI demo

This demo uses a browser website. No Android or Flutter installation is needed.

```text
Browser microphone
  -> FastAPI WebSocket
  -> Sarvam Saaras v3 realtime STT
  -> Sarvam Mayura v1 translation
  -> Sarvam Bulbul v3 TTS
  -> WebRTC teacher video + browser student subtitles and translated audio
```

## Structure

```text
.
├── main.py
├── requirements.txt
├── .env.example
└── web/index.html
```

## Sarvam configuration

Create a Sarvam API key at https://dashboard.sarvam.ai, then create `.env` beside
`main.py`:

```env
SARVAM_API_KEY=your_sarvam_subscription_key
SARVAM_TTS_SPEAKER=shubh
PORT=8000
```

The key is read only by the FastAPI process. It is never included in the
browser code or sent to the client.

The backend uses these current Sarvam interfaces:

- Realtime STT: `wss://api.sarvam.ai/speech-to-text-realtime/ws`
- STT model: `saaras:v3-realtime`
- STT configuration: `language_code=auto`, `stream_type=fast`, `encoding=linear16`,
  `sample_rate=16000`, VAD endpointing
- Translation: `POST https://api.sarvam.ai/translate`, model `mayura:v1`
- TTS: `POST https://api.sarvam.ai/text-to-speech`, model `bulbul:v3`,
  24 kHz WAV output

## Run the backend

From the project directory:

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and add SARVAM_API_KEY
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Check it with `http://127.0.0.1:8000/health`.

## Open the website on the computer

Start the backend, then open:

```text
http://127.0.0.1:8000
```

Use one browser tab as Teacher and another tab as Student.

## Open the website on another device

Find the computer's local IP:

```powershell
ipconfig
```

Look for an IPv4 address such as `192.168.1.20`. On the other device, open:

```text
http://192.168.1.20:8000
```

The computer and the other device must use the same Wi-Fi network.

Browsers normally allow microphone access only on `localhost` or HTTPS. For
the easiest test across devices, install `ngrok`, then run:

```powershell
ngrok http 8000
```

Open the generated `https://...ngrok...` URL on both devices. This also makes
the WebSocket use secure `wss://` automatically.

## Test with one teacher and one student

1. Start the backend.
2. Open the website in two browser tabs or two devices.
3. In one tab/device, use **Teacher**, then **Start lecture** and allow
   microphone access.
4. In the other tab/device, use **Student**, choose Hindi or Telugu,
   and tap **Connect to lecture**.
5. Speak a complete sentence in English or Telugu and pause briefly. Saaras
   emits a final sentence at the VAD boundary; the backend translates that
   sentence, generates Bulbul audio, and sends subtitles plus base64 WAV audio
   to the matching student.
6. Tap **Stop lecture** to close the teacher's Sarvam stream.

This intentionally supports only English/Telugu input and Hindi/Telugu student
outputs. The in-memory classroom is for this one-teacher/one-or-more-students
demo only; there is no authentication, persistence, Redis, or classroom
management.

## Video and sync

The teacher camera is sent directly to students with WebRTC. The FastAPI server
only relays WebRTC offer/answer/ICE signaling; it does not proxy or store video.
The original microphone track is not sent as classroom audio. Each final speech
sentence receives a `segment_id`; the translated subtitle is rendered just
before that segment's translated Bulbul audio starts, so the video, subtitle,
and translated audio stay aligned as a live demo.

Students enter a name and choose Hindi or Telugu before joining. The teacher
sees the live connected-student count, can mute the teacher microphone, and can
accept a named student's request to speak. After acceptance, the student's
selected-language microphone audio is transcribed by Saaras and translated to
English for the teacher transcript. The student can mute or unmute translated
audio playback.
