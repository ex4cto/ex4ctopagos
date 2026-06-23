from src.config.ajustes import Ajustes


class TestAjustesDefaults:
    def test_precio_suscripcion_cop_default(self) -> None:
        assert Ajustes.model_fields["precio_suscripcion_cop"].default == 50000

    def test_alias_suscripciones_default(self) -> None:
        assert Ajustes.model_fields["alias_suscripciones"].default == "suscripciones"

    def test_llave_cobro_operador_default_vacio(self) -> None:
        assert Ajustes.model_fields["llave_cobro_operador"].default == ""

    def test_ambiente_default_produccion(self) -> None:
        assert Ajustes.model_fields["ambiente"].default == "produccion"

    def test_webhook_token_expiracion_default(self) -> None:
        assert Ajustes.model_fields["webhook_token_expiracion_minutos"].default == 5
