# Voice Models Directory

This directory should contain your Piper TTS voice model files.

## How to Add Voice Models

1. **Download a voice model** from the [Piper voices repository](https://github.com/rhasspy/piper/releases)
   
2. **Place the files here:**
   - `your-voice-name.onnx` (the model file)
   - `your-voice-name.onnx.json` (the configuration file)

3. **Example:**
   ```bash
   # Download example voice
   wget https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx
   wget https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx.json
   ```

4. **Update environment variables** when running Docker:
   ```bash
   docker run -p 8000:8000 \
     -e API_KEYS="your-key" \
     -e VOICE_MODEL=/app/voice/en_US-lessac-medium.onnx \
     -e VOICE_CONFIG=/app/voice/en_US-lessac-medium.onnx.json \
     --name pipertts-api \
     pipertts-api
   ```

## Finding Voices

- **Browse samples:** [Piper Voice Samples](https://rhasspy.github.io/piper-samples/)
- **Download voices:** [Piper Releases](https://github.com/rhasspy/piper/releases)
- **Languages available:** English, Spanish, French, German, Italian, Portuguese, Dutch, Danish, and many more!

## Default Configuration

The Dockerfile expects these default names (you can rename your files to match):
- `/app/voice/edwin.onnx`
- `/app/voice/edwin.onnx.json`

Or override with environment variables as shown above.
