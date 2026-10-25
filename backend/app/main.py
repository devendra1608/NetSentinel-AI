from fastapi import FastAPI

app = FastAPI(
  title="NetSentinel-AI",
  description="Machine-learning-powered network intrusion detection system",
  version="0.1.0",
)

@app.get("/health", tags=["Health"])
def health_check() -> dict[str,str]:
  """Confirms that the API is running."""
  return {
    "status": "ok",
    "service": "NetSentinel-AI",
  }