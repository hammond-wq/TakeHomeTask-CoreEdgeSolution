from fastapi import APIRouter, Request, Response, status

router = APIRouter()

@router.post("/webhooks/retell")
async def retell_webhook(req: Request):
    body = await req.json()
    # TODO: verify signature; update call_log based on provider event
    return Response(status_code=status.HTTP_204_NO_CONTENT)
