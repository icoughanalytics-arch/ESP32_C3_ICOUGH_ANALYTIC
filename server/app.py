from pathlib import Path
from time import strftime

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="iCough Audio Server")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    filename = f"{strftime('%Y%m%d_%H%M%S')}{suffix}"
    output_path = UPLOAD_DIR / filename
    output_path.write_bytes(await file.read())
    return {
        "ok": True,
        "filename": filename,
        "bytes": output_path.stat().st_size,
        "download_url": f"/audio/{filename}",
    }


@app.get("/audio/{filename}")
def get_audio(filename: str):
    path = UPLOAD_DIR / filename
    return FileResponse(path, media_type="audio/wav", filename=filename)
