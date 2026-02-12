from flask import Blueprint, g, request, send_file

from app.services import get_analysis_service
from app.utils.auth import require_auth
from app.utils.errors import validation_error


export_bp = Blueprint("export", __name__)

_ALLOWED_SCOPE = {"full", "marriage_path", "challenges", "partner_character"}


@export_bp.get("/export/<int:result_id>")
@require_auth()
def export_result(result_id: int):
    scope = request.args.get("scope", "full")
    if scope not in _ALLOWED_SCOPE:
        raise validation_error("scope", "scope must be full|marriage_path|challenges|partner_character")

    service = get_analysis_service()
    current_user = getattr(g, "current_user", None) or {}
    markdown_path = service.export_markdown_file(
        result_id=result_id,
        scope=scope,
        user_id=int(current_user.get("id", 0)),
        is_admin=str(current_user.get("role", "")) == "admin",
    )
    return send_file(
        markdown_path,
        as_attachment=True,
        download_name=f"analysis_{result_id}_{scope}.md",
        mimetype="text/markdown",
    )
