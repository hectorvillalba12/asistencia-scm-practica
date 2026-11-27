## [4.0.0] - 2026-11-26
### Added
- Autenticación con usuarios, sesiones y roles (admin, docente, alumno).
- Alta de docentes, cursos, horarios e inscripciones.
- Límite de faltas por curso con estados regular / en riesgo / libre.
- Panel de informes: total y por alumno.
- Suite de tests por módulo (carpeta `tests/`).
### Changed
- La asistencia ahora se vincula a un curso (antes, a un texto de materia).
- El estado "tardanza" se calcula según el horario del curso.