# Viajes Aventura (Python + SQLite) - un archivo por módulo, todo en una carpeta

| Archivo | Contenido |
|---|---|
| `main.py` | Aplicación de consola (punto de entrada) |
| `usuario.py`, `cliente.py`, `administrador.py` | Jerarquía de usuarios (`@property`, `password_hash` como objeto hash, email con `@`) |
| `destino.py`, `paquete_turistico.py`, `reserva.py` | Clases del dominio |
| `gestor_destinos.py`, `gestor_paquetes.py`, `gestor_reservas.py` | Gestores (CRUD y reglas de negocio) |
| `servicio_autenticacion.py` | Registro, login, bloqueo y cambio de contraseña |
| `seguridad.py` | `HashContraseña` (PBKDF2-HMAC-SHA256 con salt) |
| `validador.py` | Validaciones de entrada |
| `base_datos.py` | Persistencia SQLite |
| `errores.py`, `configuracion.py` | Excepciones y configuración |
| `test_sistema.py` | 31 pruebas |

```
python main.py                      # ejecutar
python -m unittest test_sistema     # pruebas
```
La base de datos (`viajes_aventura.db`) y el log (`viajes.log`) se crean en la misma carpeta.
Solo usa la librería estándar.
