# Guía de Contribución a ModelRouter

¡Gracias por tu interés en contribuir a ModelRouter!

## Código de Conducta

Este proyecto se adhiere a un código de conducta. Al participar, se espera que mantengas un ambiente respetuoso y constructivo.

## Cómo Contribuir

### Reportar Bugs

1. Verifica que el bug no haya sido reportado en [Issues](https://github.com/HC-ONLINE/ModelRouter/issues)
2. Abre un nuevo issue con:
   - Descripción clara del problema
   - Pasos para reproducir
   - Comportamiento esperado vs. real
   - Versiones (Python, OS, dependencias)
   - Logs relevantes (sin datos sensibles)

### Proponer Features

1. Abre un issue con etiqueta "enhancement"
2. Describe el caso de uso
3. Propón una solución
4. Espera feedback antes de implementar

### Pull Requests

1. **Fork el repositorio**
2. **Crea una rama** desde `main` o `develop`:

   ```bash
   git checkout -b feature/mi-feature
   ```

3. **Implementa cambios**:

   - Sigue el estilo de código existente
   - Añade tests para nuevo código
   - Actualiza documentación si es necesario

4. **Ejecuta tests y lint**:

   ```bash
   python scripts/test.py all
   ```

5. **Commit con mensajes descriptivos**:

   ```bash
   git commit -m "feat: añade soporte para provider X"
   ```

6. **Push a tu fork**:

   ```bash
   git push origin feature/mi-feature
   ```

7. **Abre Pull Request** hacia `main` o `develop` con descripción detallada de los cambios.

## Estándares de Código

### Python

- **Formato**: Black con line-length=88
- **Linting**: Flake8
- **Type hints**: Obligatorio en funciones públicas
- **Docstrings**: Google style para módulos/clases/funciones

### Tests

- Coverage mínimo: 80%
- Tests unitarios para lógica de negocio
- Tests de integración para endpoints
- Mocks para dependencias externas (Redis, HTTP)

### Commits

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nueva funcionalidad
- `fix:` Corrección de bug
- `docs:` Cambios en documentación
- `test:` Añadir/modificar tests
- `refactor:` Refactorización sin cambio de funcionalidad
- `chore:` Tareas de mantenimiento

## Proceso de Revisión

1. Los mantainers revisarán tu PR
2. Puede haber comentarios/sugerencias
3. Actualiza tu PR según feedback
4. Una vez aprobado, se mergeará

## Configuración del Entorno de Desarrollo

```bash
# Clonar
git clone https://github.com/HC-ONLINE/ModelRouter.git
cd ModelRouter

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias + dev tools
pip install -r requirements-dev.txt

# Configurar pre-commit hooks (recomendado)
pip install pre-commit
pre-commit install
```

## Preguntas

Si tienes dudas, abre un issue con etiqueta "question" o únete a [Discussions](https://github.com/HC-ONLINE/ModelRouter/discussions).

---

¡Gracias por contribuir!
