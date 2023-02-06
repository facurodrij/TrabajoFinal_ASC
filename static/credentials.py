class MercadoPagoCredentials:
    """
    Clase para obtener sus credenciales de MercadoPago
    """
    public_key = 'YOUR_PUBLIC_KEY'  # Inserte aquí su public_key
    access_token = 'YOUR_ACCESS_TOKEN'  # Inserte aquí su access_token

    @classmethod
    def get_public_key(cls):
        return cls.public_key

    @classmethod
    def get_access_token(cls):
        return cls.access_token
