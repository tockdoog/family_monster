# backend/app/shared/idempotency.py
# Protección contra solicitudes duplicadas: el cliente envía una clave única (Idempotency-Key)
# por operación; repetir la misma clave con los mismos datos devuelve el resultado original.

import hashlib
import json
from typing import Annotated, Any

from fastapi import Header

# Solo caracteres seguros y longitud acotada (se guarda en base de datos).
_PATRON_CLAVE = r"^[A-Za-z0-9_\-]{8,80}$"

# Cabecera obligatoria en las operaciones que mueven dinero.
ClaveIdempotencia = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        pattern=_PATRON_CLAVE,
        description="Identificador único de la operación (8 a 80 caracteres: letras, números, - y _).",
    ),
]


def calcular_huella(operacion: str, **partes: Any) -> str:
    """Huella SHA-256 de la solicitud: detecta si una clave se reutiliza con datos distintos."""
    texto = json.dumps({"op": operacion, **partes}, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()