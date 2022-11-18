from fastapi import APIRouter, Header, HTTPException
from starlette.responses import FileResponse, PlainTextResponse

from ice.trace import trace_dir

router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.get("/")
async def list_traces():
    # e.g. if trace_dir contains files trace1.jsonl, trace2.jsonl, other.txt,
    # return ["trace1", "trace2"]
    return [trace.stem for trace in trace_dir.glob("*.jsonl")]


@router.get("/{trace_id}.jsonl")
async def get_trace(trace_id: str, Range: str | None = Header(None)):
    path = trace_dir / f"{trace_id}.jsonl"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Trace not found")

    if Range is None:
        return FileResponse(path)

    try:
        start, end = map(int, Range.removeprefix("bytes=").split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Range header")

    with open(path, "rb") as f:
        f.seek(start)
        length = end - start + 1
        byts = f.read(length)
        text = byts.decode("utf-8", errors="ignore")
        return PlainTextResponse(text, status_code=206)