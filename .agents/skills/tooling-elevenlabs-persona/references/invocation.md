# Invocation pattern

Fetch the voice id from SSM, then call the MCP:

```bash
VOICE_ID=$(ward ops aws ssm get-parameter \
  --name /elevenlabs/voice-id/default --with-decryption \
  --query Parameter.Value --output text)
mcporter call "elevenlabs.text_to_speech(text: \"<persona-shaped line>\", voice_id: \"$VOICE_ID\", output_directory: \"/Users/kai/data/elevenlabs\")"
```

If the shell has been seeded with `ssm-load`, the parameter is already exported as `ELEVENLABS_VOICE_ID_DEFAULT` and the first command can be skipped.

## Sample lines, in voice

- "Voice channel established. Substrate online."
- "A search of the repository was performed via ripgrep. Three matches were located."
- "The build was kicked off. Output is being captured."
- "The page was curled. Status was two hundred."
- "A snapshot of the dashboard was taken via webdriver. Three panels rendered."
- "The deploy completed cleanly. Sentry has remained quiet."
- "Two pull requests are open. Neither has been reviewed."
- "An attempt to fetch the model list will be made shortly."
