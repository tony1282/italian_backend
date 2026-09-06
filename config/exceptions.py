class BusinessException(Exception):
    """
    Excepción para errores de negocio esperados.
    Debe lanzarse cuando una operación no puede completarse
    por una regla de negocio (estado inválido, stock insuficiente,
    plazo vencido, etc.).
    Las vistas la capturan y responden con HTTP 400.
    """

    def __init__(self, message, data=None):
        super().__init__(message)
        self.data = data
