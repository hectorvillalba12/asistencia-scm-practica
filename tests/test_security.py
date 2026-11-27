from backend import security


def test_hash_y_verificacion_correcta():
    almacenado = security.hashear_password("clave12345")
    assert security.verificar_password("clave12345", almacenado)


def test_password_incorrecta():
    almacenado = security.hashear_password("clave12345")
    assert not security.verificar_password("otra-clave", almacenado)


def test_mismo_password_genera_hashes_distintos():
    assert security.hashear_password("abc") != security.hashear_password("abc")


def test_hash_malformado_no_rompe():
    assert not security.verificar_password("x", "esto-no-es-un-hash")


def test_tokens_unicos():
    assert security.generar_token() != security.generar_token()
    assert len(security.generar_token()) >= 32