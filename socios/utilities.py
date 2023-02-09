#  Este archivo contiene funciones de utilidad para la app socios

from django.db.models import Q

from core.models import Persona
from socios.models import Categoria


def get_categoria(persona=None, edad=None):
    """
    Devuelve las categorias que puede elegir un socio con base en su edad.
    :param edad:
    :param persona: persona.id
    :return: Categoria
    """
    lista_categorias = []
    if persona:
        edad = Persona.objects.get(pk=persona).get_edad()
    # Obtener las categorias que corresponden a la edad,
    # incluyendo la primera categoria (Sin Categoria)
    categorias = Categoria.objects.filter((Q(edad_desde__lte=edad) & Q(edad_hasta__gte=edad)) | Q(pk=1))
    for categoria in categorias:
        item = categoria.toJSON()
        lista_categorias.append(item)
    return lista_categorias
