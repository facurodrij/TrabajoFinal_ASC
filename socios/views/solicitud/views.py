from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.generic import ListView, CreateView

from accounts.models import User, Persona
from core.models import Club
from socios.forms import SolicitudForm
from socios.models import SolicitudSocio, Categoria, Estado, Socio


class SolicitudView(CreateView):
    """
    Vista que permite a una persona solicitar su ingreso como socio.
    """
    model = SolicitudSocio
    form_class = SolicitudForm
    template_name = 'solicitud/solicitud.html'
    success_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super(SolicitudView, self).get_context_data(**kwargs)
        context['title'] = 'Solicitud de asociación'
        context['club'] = Club.objects.get(pk=1)
        context['action'] = 'add'
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                form = self.form_class(request.POST, request.FILES)
                if form.is_valid():
                    with transaction.atomic():
                        solicitud = form.save(commit=False)
                        solicitud.club = Club.objects.get(pk=1)
                        solicitud.save()
                        messages.success(request, 'Solicitud enviada correctamente')
                else:
                    data['error'] = form.errors
            elif action == 'get_categoria':
                data = []
                fecha_nacimiento = request.POST['fecha_nacimiento']
                edad = relativedelta(datetime.now(), datetime.strptime(fecha_nacimiento, '%d/%m/%Y')).years
                # Obtener las categorias que corresponden a la edad
                categorias = Categoria.objects.filter(edad_desde__lte=edad,
                                                      edad_hasta__gte=edad)
                for categoria in categorias:
                    item = categoria.toJSON()
                    data.append(item)
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)


class SolicitudListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista que lista las solicitudes de asociación.
    """
    model = SolicitudSocio
    template_name = 'solicitud/list.html'
    permission_required = 'socios.view_solicitudsocio'
    context_object_name = 'solicitudes'

    def get_queryset(self):
        return SolicitudSocio.global_objects.all()

    def get_context_data(self, **kwargs):
        context = super(SolicitudListView, self).get_context_data(**kwargs)
        context['title'] = 'Listado de solicitudes de asociación'
        return context

    # Sobreescribir el método get para recibir solicitudes ajax, si no es ajax, se ejecuta el método get de la clase padre
    def get(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.GET['action']
            if action == 'get_detail':
                # Enviar los datos de la solicitud en formato json
                data = []
                solicitud = SolicitudSocio.global_objects.get(pk=request.GET['id'])
                item = solicitud.toJSON()
                data.append(item)
            elif action == 'rechazar':
                # Si la acción es Rechazar, se elimina la solicitud
                solicitud = SolicitudSocio.objects.get(pk=request.GET['id'])
                solicitud.delete()
                messages.success(request, 'Solicitud rechazada correctamente')
            elif action == 'aprobar':
                solicitud = SolicitudSocio.objects.get(pk=request.GET['id'])
                solicitud.is_aprobado = True
                try:
                    persona = Persona(dni=solicitud.dni,
                                      sexo=solicitud.sexo,
                                      club=solicitud.club,
                                      nombre=solicitud.nombre,
                                      apellido=solicitud.apellido,
                                      fecha_nacimiento=solicitud.fecha_nacimiento,
                                      imagen=solicitud.imagen)
                    estado = Estado.objects.get(code='AD')
                    socio = Socio(persona=persona,
                                  categoria=solicitud.categoria,
                                  estado=estado)
                    password = User.objects.make_random_password()
                    user = User(persona=persona,
                                username=solicitud.dni,
                                email=solicitud.email,
                                password=password)
                except Exception as e:
                    messages.error(request, 'Error al crear usuario. {}'.format(e))
                    return redirect('solicitud_list')
                # Guardar los datos, si hay error, deshacer la transacción
                try:
                    with transaction.atomic():
                        persona.save()
                        socio.save()
                        user.save()
                        solicitud.save()
                    # Enviar un Email al Usuario con un enlace para cambiar su contraseña
                    current_site = get_current_site(request)
                    mail_subject = 'Active su cuenta.'
                    message = render_to_string('email/activate_account.html', {
                        'user': user,
                        'domain': current_site.domain,
                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                        'token': PasswordResetTokenGenerator().make_token(user),
                        'protocol': 'https' if request.is_secure() else 'http',
                    })
                    to_email = solicitud.email
                    email = EmailMessage(
                        mail_subject, message, to=[to_email]
                    )
                    email.send()
                    messages.success(request,
                                     'Solicitud aprobada correctamente. '
                                     'Se ha enviado un email al usuario para que cambie su contraseña')
                except IntegrityError as e:
                    messages.error(request, 'Error al aprobar la solicitud. {}'.format(e))
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
            return super(SolicitudListView, self).get(request, *args, **kwargs)
        return JsonResponse(data, safe=False)
