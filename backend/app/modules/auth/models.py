# backend/app/modules/auth/models.py
# Tablas de identidad: usuarios con acceso a la app y control de intentos de inicio de sesión.

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdUuidMixin, MarcaTiempoMixin


class Usuario(IdUuidMixin, MarcaTiempoMixin, Base):
    """Persona con credenciales para entrar a la aplicación."""

    __tablename__ = "users"

    # Correo siempre en minúsculas: evita duplicados como Ana@x.com y ana@x.com.
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    # Solo se guarda el hash Argon2id, jamás la contraseña.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(120), nullable=False)
    # Desactivar un usuario bloquea su acceso sin borrar su historial.
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())

    __table_args__ = (
        UniqueConstraint("email"),
        CheckConstraint("email = lower(email)", name="email_minusculas"),
        CheckConstraint("length(trim(nombre_completo)) > 0", name="nombre_no_vacio"),
    )


class IntentoLogin(Base):
    """Contador de intentos fallidos por correo (existente o no) para frenar la fuerza bruta.

    La clave es un hash del correo, así el comportamiento es idéntico para cuentas
    reales e inexistentes y no se puede usar para descubrir qué correos están registrados.
    """

    __tablename__ = "login_attempts"

    clave: Mapped[str] = mapped_column(String(64), primary_key=True)
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    primer_intento_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (CheckConstraint("intentos >= 0", name="intentos_no_negativos"),)