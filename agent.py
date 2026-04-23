import logging
import os
from contextlib import asynccontextmanager

import anthropic
from fastapi import FastAPI, HTTPException
from anthropic import APIStatusError
from pydantic import BaseModel

from pact_sdk import PACTClient

REGISTRY_URL = "http://localhost:8000"
AGENT_ID = "agent_summarizer_01"
AGENT_PORT = 8001

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

pact = PACTClient(REGISTRY_URL)
claude = anthropic.Anthropic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    result = pact.register(
        agent_id=AGENT_ID,
        org_name="Summarization Services",
        org_domain="summarizer.local",
        contact_email="admin@summarizer.local",
    )
    if "error" in result:
        log.warning("PACT registration skipped: %s", result["error"])
    else:
        log.info("Registered with PACT registry: %s", result.get("status"))
    yield


app = FastAPI(title="Summarization Agent", version="1.0.0", lifespan=lifespan)


class TaskRequest(BaseModel):
    text: str
    max_words: int = 100


class TaskResponse(BaseModel):
    agent_id: str
    summary: str


@app.post("/task", response_model=TaskResponse)
def run_task(body: TaskRequest):
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")

    try:
        response = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": "You are a summarization assistant. Return only the summary — no preamble, no labels.",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Summarize the following text in at most {body.max_words} words:\n\n{body.text}"
                    ),
                }
            ],
        )
    except APIStatusError as e:
        log.error("Anthropic API error %s: %s", e.status_code, e.message)
        raise HTTPException(status_code=502, detail=f"Upstream AI error: {e.message}")

    return TaskResponse(agent_id=AGENT_ID, summary=response.content[0].text)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("agent:app", host="0.0.0.0", port=AGENT_PORT, reload=True)
