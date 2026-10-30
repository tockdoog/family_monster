# backend/tests/modules/test_integridad_bd.py
# Pruebas de las restricciones de la base de datos: son la última barrera si el código falla.

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.modules.auth.models import Usuario
from app.modules.households.models import Hogar, Membresia
from app.modules.members.models import Integrante


def _usuario_id(sesion, email: str):
    """Id de un usuario por correo."""
    return sesion.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email}).scalar_one()


def test_integrante_no_puede_vincular_un_usuario_de_otro_hogar(crear_hogar, sesion):
    """La llave compuesta impide mezclar el usuario de un hogar con otro hogar."""
    hogar_a = crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    hogar_b = crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    usuario_a = _usuario_id(sesion, "ana@example.com")
    sesion.add(Integrante(household_id=hogar_b.id, nombre="Impostor", user_id=usuario_a))
    with pytest.raises(IntegrityError):
        sesion.flush()
    sesion.rollback()
    assert hogar_a.id != hogar_b.id


def test_un_usuario_no_puede_tener_dos_membresias(crear_hogar, sesion):
    """En la versión 1 cada usuario pertenece a un solo hogar."""
    crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    hogar_b = crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    sesion.add(Membresia(user_id=_usuario_id(sesion, "ana@example.com"), household_id=hogar_b.id, rol="miembro"))
    with pytest.raises(IntegrityError):
        sesion.flush()
    sesion.rollback()


def test_rol_invalido_es_rechazado_por_la_base(crear_hogar, sesion):
    """Solo existen los roles admin y miembro."""
    crear_hogar()
    with pytest.raises(IntegrityError):
        sesion.execute(text("UPDATE memberships SET rol = 'superusuario'"))
    sesion.rollback()


def test_correo_con_mayusculas_es_rechazado_por_la_base(bd, sesion):
    """La base impide guardar correos que no estén en minúsculas."""
    sesion.add(Usuario(email="Ana@example.com", password_hash="x", nombre_completo="Ana"))
    with pytest.raises(IntegrityError):
        sesion.flush()
    sesion.rollback()


def test_moneda_distinta_de_cop_es_rechazada(bd, sesion):
    """La versión 1 solo admite pesos colombianos."""
    sesion.add(Hogar(nombre="Hogar USD", moneda="USD"))
    with pytest.raises(IntegrityError):
        sesion.flush()
    sesion.rollback()


def test_no_se_puede_borrar_un_hogar_con_integrantes(crear_hogar, sesion):
    """El borrado está restringido: los datos financieros no se pierden en cascada."""
    crear_hogar()
    with pytest.raises(IntegrityError):
        sesion.execute(text("DELETE FROM households"))
    sesion.rollback()


def test_nombre_de_integrante_en_blanco_es_rechazado(crear_hogar, sesion):
    """No se aceptan nombres vacíos ni de solo espacios."""
    hogar = crear_hogar()
    sesion.add(Integrante(household_id=hogar.id, nombre="   "))
    with pytest.raises(IntegrityError):
        sesion.flush()
    sesion.rollback()