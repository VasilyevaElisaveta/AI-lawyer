import sys
from pathlib import Path
from pydantic import BaseModel

import fastapi

from ..graph import ContractAgent


class MessageRequest(BaseModel):
    user_id: str
    user_message: str


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

app = fastapi.FastAPI()
contract_agent = ContractAgent()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/contract_agent")
async def contract_agent_endpoint(request: MessageRequest):
    result = await contract_agent.process_user_message(
        user_message=request.user_message,
        thread_id=request.user_id,
    )
    return {
        "request": request,
        "response": result
    }