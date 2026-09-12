"""مسارات فحص صحة واستعداد خدمة مصنع المحتوى."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["system"])


@router.get("/api/v1/health")
def health(request: Request) -> dict:
    """يعيد حالة الخدمة الأساسية دون الحاجة إلى مزود ذكاء اصطناعي خارجي."""
    return {
        "status": "ok",
        "data": {"status": "OK", "service": "ai-content-factory-backend"},
        "requestId": request.state.request_id,
    }


@router.get("/api/v1/ready", response_model=None)
def readiness(request: Request) -> dict | JSONResponse:
    """يتحقق من جاهزية مخزن البيانات قبل قبول العمل الجديد."""
    try:
        from ...main import repositories

        repositories.store.connection.execute("SELECT 1").fetchone()
        return {
            "status": "ready",
            "data": {"status": "READY", "service": "ai-content-factory-backend"},
            "requestId": request.state.request_id,
        }
    except Exception:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "RESOURCE_UNAVAILABLE",
                    "message": "Required dependencies are not ready",
                    "details": {},
                    "requestId": request_id,
                }
            },
            headers={"X-Request-Id": request_id},
        )


@router.get("/api/v1/readiness", include_in_schema=False, response_model=None)
def readiness_alias(request: Request) -> dict | JSONResponse:
    """يوفر المسار القديم لفحص الجاهزية مع نفس آلية الفحص الأساسية."""
    return readiness(request)
