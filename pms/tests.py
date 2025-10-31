from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import Room, Room_type, Booking, Customer
from django.contrib.auth.models import User

class EditBookingDatesTest(TestCase):
    def setUp(self):
        # Crear tipo de habitación
        self.room_type = Room_type.objects.create(
            name='Simple',
            price=20.00,
            max_guests=1,
        )
        
        # Crear habitación
        self.room = Room.objects.create(
            room_type=self.room_type,
            name='Habitación Room 1.4',
            description='Lorem ipsum dolor sit amet...'
        )
        
        # Crear cliente
        self.customer = Customer.objects.create(
            name='Chapp Test',
            email='asd@as.es',
            phone='1'
        )
        
        # Fechas para las pruebas
        self.today = timezone.now().date()
        self.tomorrow = self.today + timedelta(days=1)
        
        # Crear reserva de prueba
        self.booking = Booking.objects.create(
            room=self.room,
            customer=self.customer,
            checkin=self.today,
            checkout=self.tomorrow,
            guests=1,
            total=20.00,
            code='KC966KUI',
            state='NEW'
        )
        
        # URL para editar fechas 
        self.edit_dates_url = reverse('edit_booking_dates', kwargs={'pk': self.booking.id})
        
    def test_edit_booking_dates_view_GET(self):
        """Prueba que la vista de edición de fechas se carga correctamente"""
        response = self.client.get(self.edit_dates_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'edit_booking_dates.html')
        self.assertContains(response, 'Editar Fechas de la Reserva')
    
    def test_edit_booking_dates_valid_POST(self):
        """Prueba la edición exitosa de fechas"""
        new_checkin = self.today + timedelta(days=5)
        new_checkout = self.today + timedelta(days=7)
        
        response = self.client.post(self.edit_dates_url, {
            'checkin': new_checkin,
            'checkout': new_checkout
        })
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        
        # Actualizar objeto de la base de datos
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.checkin, new_checkin)
        self.assertEqual(self.booking.checkout, new_checkout)
    
    def test_edit_booking_dates_invalid_dates(self):
        """Prueba que no se puedan guardar fechas inválidas"""
        response = self.client.post(self.edit_dates_url, {
            'checkin': self.tomorrow,
            'checkout': self.today  # Fecha de salida anterior a la de entrada
        }, follow=True)  # Añadido follow=True para seguir la redirección
        
        # Verificar que se muestre el mensaje de error
        self.assertContains(response, 'La fecha de salida debe ser posterior a la fecha de entrada.')
        
        