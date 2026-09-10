# Artifact preview clip

`artifact-preview.mp4` is a synthetic one-second teal frame, 64×64 pixels,
H.264/YUV420P at 5 fps. It contains no user content or external media.
The artifact browser test needs a decodable file, not just an MP4 header:
otherwise the native media error event races its assertions.

Regenerate from the repository root:

```sh
ffmpeg -hide_banner -loglevel error -f lavfi -i color=c=teal:s=64x64:r=5 -t 1 -c:v libx264 -pix_fmt yuv420p -movflags +faststart client/e2e/fixtures/artifact-preview.mp4
```
