# PiperTTS API (Dockerized)

FastAPI service for text-to-speech synthesis using PiperTTS.

## Features

- 🎙️ High-quality text-to-speech synthesis using PiperTTS
- 🔐 API key authentication
- 🚀 FastAPI with async support
- 🐳 Fully containerized with Docker
- 📝 Simple API with sensible defaults
- 🔧 Configurable speech parameters

## Prerequisites

**Important:** This repository does not include voice models. You must download and add your own Piper voice models before building the Docker container.

### Adding Voice Models

1. Download a Piper voice model from the [Piper voices repository](https://github.com/rhasspy/piper/releases)
2. Place both the `.onnx` and `.onnx.json` files in the `voice/` directory
3. Update the `VOICE_MODEL` and `VOICE_CONFIG` environment variables in your Docker run command to match your voice file names

Example:
```bash
# Download a voice (example)
cd voice/
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx.json
cd ..
```

The voice files are gitignored to keep the repository lightweight and allow users to choose their preferred voices.

## Endpoints

- `GET /health` → `{ status, model, voice }`
- `GET /help` → Complete API documentation and usage examples
- `POST /speak` (requires `x-api-key`)
  - Body: `{ "text": string, "speaker"?: int, "noise_scale"?: float, "length_scale"?: float, "noise_w"?: float }`
  - Response: WAV audio file

## Authentication

- Header `x-api-key` must match one in `API_KEYS` (comma-separated env variable).

## Environment Variables

- **API_KEYS**: Comma-separated list of allowed API keys used for `x-api-key` auth. Example: `API_KEYS="key1,key2"`.
- **VOICE_MODEL**: Path to the Piper ONNX model file (default: `/app/voice/edwin.onnx`).
- **VOICE_CONFIG**: Path to the Piper model config JSON file (default: `/app/voice/edwin.onnx.json`).

### Generate API Keys (Linux)

```bash
openssl rand -hex 32
# Multiple keys example
API_KEYS="$(openssl rand -hex 32),$(openssl rand -hex 32)"
```

## Build

**Note:** Ensure you have added voice model files to the `voice/` directory before building!

```bash
DOCKER_BUILDKIT=1 docker build -t pipertts-api .
```

## Run

Basic usage with default voice paths:

```bash
docker run -p 8000:8000 \
  -e API_KEYS="dev-key" \
  --name pipertts-api \
  pipertts-api
```

With custom voice model paths (update to match your voice file names):

```bash
docker run -p 8000:8000 \
  -e API_KEYS="dev-key" \
  -e VOICE_MODEL=/app/voice/en_US-lessac-medium.onnx \
  -e VOICE_CONFIG=/app/voice/en_US-lessac-medium.onnx.json \
  --name pipertts-api \
  pipertts-api
```

Or with multiple API keys:

```bash
docker run -p 8000:8000 \
  -e API_KEYS="key1,key2,key3" \
  -e VOICE_MODEL=/app/voice/en_US-lessac-medium.onnx \
  -e VOICE_CONFIG=/app/voice/en_US-lessac-medium.onnx.json \
  --name pipertts-api \
  pipertts-api
```

## Test

```bash
# Health check
curl http://localhost:8000/health

# Get help
curl http://localhost:8000/help

# Generate speech (minimal - only text required)
curl -X POST http://localhost:8000/speak \
  -H 'content-type: application/json' \
  -H 'x-api-key: dev-key' \
  -d '{"text":"Hello, world!"}' \
  --output speech.wav

# Generate speech with custom parameters
curl -X POST http://localhost:8000/speak \
  -H 'content-type: application/json' \
  -H 'x-api-key: dev-key' \
  -d '{
    "text": "This is a test of the Piper text to speech system.",
    "speaker": 0,
    "noise_scale": 0.667,
    "length_scale": 1.0,
    "noise_w": 0.8
  }' \
  --output speech.wav

# Play the audio (Linux with aplay)
aplay speech.wav

# Play the audio (macOS)
afplay speech.wav
```

## API Parameters

### `/speak` endpoint

- **text** (required): The text to convert to speech
- **speaker** (optional, default: 0): Speaker ID for multi-speaker models
- **noise_scale** (optional, default: 0.667): Controls variability in the generated speech
- **length_scale** (optional, default: 1.0): Controls speaking speed (< 1.0 = faster, > 1.0 = slower)
- **noise_w** (optional, default: 0.8): Controls phoneme duration variation

## Development

### Run locally without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export API_KEYS="dev-key"

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Voice Models

This repository does not include pre-packaged voice models. You must add your own:

1. Download voice models from [Piper voices repository](https://github.com/rhasspy/piper/releases)
2. Place the `.onnx` and `.onnx.json` files in the `voice/` directory
3. Update the `VOICE_MODEL` and `VOICE_CONFIG` environment variables to match your file names

**Available Voices:** Browse the [Piper voices catalog](https://rhasspy.github.io/piper-samples/) to hear samples and choose voices.

**Default paths in Dockerfile:**
- `VOICE_MODEL=/app/voice/edwin.onnx`
- `VOICE_CONFIG=/app/voice/edwin.onnx.json`

If your voice files have different names, either rename them to match or override via environment variables when running the container.

## Notes

- The service does not store requests or audio results.
- Audio is generated on-demand and streamed as WAV format.
- All optional parameters have sensible defaults based on the voice model configuration.
- The `/help` endpoint provides complete API documentation accessible without authentication.

## License

MIT License - See LICENSE file for details.
