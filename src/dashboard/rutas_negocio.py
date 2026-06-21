from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from src.config.base_datos import obtener_sesion
from src.dashboard.jinja import templates
from src.repositorios import cliente_repo, pago_repo

enrutador = APIRouter(tags=["dashboard"])


@enrutador.get("/dashboard/{token}", response_class=HTMLResponse)
def dashboard_negocio(
    token: UUID,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
) -> HTMLResponse:
    cliente = cliente_repo.obtener_por_token_dashboard(token, sesion)
    if not cliente:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "mensaje": "Dashboard no encontrado o enlace inválido."},
            status_code=404,
        )

    ahora = datetime.now(timezone.utc)
    metricas = pago_repo.calcular_metricas(cliente.id, ahora, sesion)
    pagos = pago_repo.listar_por_cliente(
        cliente.id,
        desde=datetime(2020, 1, 1, tzinfo=timezone.utc),
        hasta=ahora,
        sesion=sesion,
        limite=100,
    )

    return templates.TemplateResponse(
        "negocio/inicio.html",
        {
            "request": request,
            "cliente": cliente,
            "metricas": metricas,
            "pagos": pagos,
        },
    )
