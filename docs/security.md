# Seguridad

Pautas mínimas de seguridad y manejo de secretos para ModelRouter.

- Nunca subir claves API en el repositorio.
- Usar variables de entorno o un secreto manager en producción.
- Validar y filtrar datos sensibles antes de loggear.
- Respetar los TOS y rate limits de cada proveedor; no usar esta herramienta para evadir límites.

## Recomendaciones

- Monitorizar logs y alertas por errores de proveedor y latencias.
- Restringir el acceso a la API con `API_KEY` y/o un proxy autenticador.
- En entornos multi-tenant, separar límites y cuotas por tenant.
- Usar HTTPS para todas las comunicaciones externas e internas.

---

## Disclaimer Legal

Este proyecto es para **uso personal**. Asegúrate de:

- Leer y cumplir los **Terms of Service** de los proveedores usados
- No usar rotación de proveedores para **evadir límites** de uso
- Respetar **rate limits** y políticas de cada proveedor
- No almacenar/procesar datos sensibles sin las medidas de seguridad apropiadas

**El autor no se hace responsable del uso indebido de esta herramienta.**

---

Ver [README.md](../README.md) para más detalles legales y de licencia. o Ver el [ROADMAP.md](../ROADMAP.md) para próximos pasos del proyecto.
