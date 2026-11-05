import pytest
from main import registrar_asistencia, obtener_reporte_estadistico, historial_registros, total_asistencias

@pytest.fixture(autouse=True)
def limpiar_estado():
    """
    Fixture que limpia y restablece las variables globales de estado 
    antes de cada ejecución de prueba para asegurar el aislamiento.
    """
    global total_asistencias, historial_registros
    total_asistencias = 0
    historial_registros.clear()
    yield

def test_registrar_asistencia_exitoso():
    """
    Verifica que una asistencia con un DNI válido y materia predeterminada 
    se registre correctamente y devuelva True.
    """
    alumno = {"dni": "40123456", "materia": "Programación III"}
    resultado = registrar_asistencia(alumno)
    
    assert resultado is True
    assert total_asistencias == 1
    assert len(historial_registros) == 1
    assert historial_registros[0]["dni"] == "40123456"
    assert historial_registros[0]["materia"] == "Programación III"

def test_registrar_asistencia_materia_personalizada():
    """
    Verifica que se pueda registrar una asistencia con una materia específica.
    """
    alumno = {"dni": "38999111", "materia": "Práctica Profesional II"}
    resultado = registrar_asistencia(alumno)
    
    assert resultado is True
    assert historial_registros[0]["materia"] == "Práctica Profesional II"

def test_registrar_asistencia_dni_invalido_corto():
    """
    Verifica que se rechace un DNI con menos de 7 dígitos y devuelva False.
    """
    alumno = {"dni": "123", "materia": "Programación III"}
    resultado = registrar_asistencia(alumno)
    
    assert resultado is False
    assert total_asistencias == 0
    assert len(historial_registros) == 0

def test_registrar_asistencia_dni_con_letras():
    """
    Verifica que un DNI que contenga caracteres no numéricos sea rechazado.
    """
    alumno = {"dni": "40123ABC", "materia": "Programación III"}
    resultado = registrar_asistencia(alumno)
    
    assert resultado is False
    assert total_asistencias == 0

def test_registrar_asistencia_sin_dni():
    """
    Verifica que la función maneje correctamente la ausencia del campo DNI.
    """
    alumno = {"materia": "Programación III"}
    resultado = registrar_asistencia(alumno)
    
    assert resultado is False
    assert total_asistencias == 0

def test_obtener_reporte_estadistico():
    """
    Verifica que el reporte estadístico devuelva correctamente el total
    y el detalle de los registros acumulados.
    """
    registrar_asistencia({"dni": "40123456", "materia": "Programación III"})
    registrar_asistencia({"dni": "41222333", "materia": "Práctica Profesional II"})
    
    reporte = obtener_reporte_estadistico()
    
    assert reporte["total_asistencias"] == 2
    assert len(reporte["detalle"]) == 2
    assert reporte["detalle"][0]["dni"] == "40123456"
    assert reporte["detalle"][1]["dni"] == "41222333"