from fastapi import APIRouter, Request, Response, status

router = APIRouter()

@router.post("/webhooks/retell")
async def retell_webhook(req: Request):
    body = await req.json()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
