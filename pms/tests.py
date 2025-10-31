from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import Room, Room_type, Booking, Customer

@override_settings(DEBUG=True)
class RoomFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Crear tipo de habitación
        cls.room_type = Room_type.objects.create(
            name="Doble",
            price=30.0,
            max_guests=2
        )
        cls.room1 = Room.objects.create(name="Room 2.1", room_type=cls.room_type)
        cls.client = Client()

    def test_filter_by_name(self):
        """Filtrado normal por nombre"""
        response = self.client.get(reverse('rooms') + '?q=2.1')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Room 2.1")

    def test_filter_by_name_ajax(self):
        """Filtrado AJAX por nombre"""
        response = self.client.get(
            reverse('rooms') + '?q=2.1',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertIn('rooms', data)
        rooms = data['rooms']
        self.assertTrue(any(room['name'] == 'Room 2.1' for room in rooms))
@override_settings(DEBUG=True)
class DashboardTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create room types
        cls.room_type_single = Room_type.objects.create(
            name="Simple",
            price=20.0,
            max_guests=1
        )
        cls.room_type_double = Room_type.objects.create(
            name="Doble",
            price=30.0,
            max_guests=2
        )
        cls.room_type_triple = Room_type.objects.create(
            name="Triple",
            price=40.0,
            max_guests=3
        )
        cls.room_type_quadruple = Room_type.objects.create(
            name="Cuádruple",
            price=50.0,
            max_guests=4
        )

    def setUp(self):
        self.client = Client()
        
        # Rooms pattern
        rooms_pattern = [
            # Floor 1 (10 rooms)
            *[f"1.{i+1}" for i in range(10)],
            # Floor 2 (5 rooms)
            *[f"2.{i+1}" for i in range(5)],
            # Piso 3 (4 habitaciones)
            *[f"3.{i+1}" for i in range(4)],
            # Floor 4 (6 rooms)
            *[f"4.{i+1}" for i in range(6)],
        ]
        
        # Create rooms
        for room_name in rooms_pattern:
            Room.objects.create(
                name=f"Room {room_name}",
                room_type=self.room_type_double if int(room_name.split('.')[-1]) % 2 == 0 else self.room_type_single
            )

        # Dates
        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Create confirmed booking for the first room
        Booking.objects.create(
            room=Room.objects.get(name="Room 2.1"),
            checkin=today,
            checkout=tomorrow,
            state="CONF",
            total=30.0,
            guests=2
        )

    def test_dashboard_occupancy_rate(self):
        """Should calculate the occupancy rate correctly"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        dashboard = response.context['dashboard']

        # Verify expected values
        self.assertEqual(dashboard['total_rooms'], 25)
        self.assertEqual(dashboard['occupied_rooms'], 1)
        self.assertAlmostEqual(dashboard['occupancy_rate'], 4.0, places=1)  # 1/25 = 4%

# Edit Booking Dates Test- branch feature/03-edit-booking-dates
class EditBookingDatesTest(TestCase):
    def setUp(self):
        # Create room type
        self.room_type = Room_type.objects.create(
            name='Simple',
            price=20.00,
            max_guests=1,
        )
        
        # Create room
        self.room = Room.objects.create(
            room_type=self.room_type,
            name='Habitación Room 1.4',
            description='Lorem ipsum dolor sit amet...'
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            name='Chapp Test',
            email='asd@as.es',
            phone='1'
        )
        
        # Dates for tests
        self.today = timezone.now().date()
        self.tomorrow = self.today + timedelta(days=1)
        
        # Create booking
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
        
        # URL to edit dates 
        self.edit_dates_url = reverse('edit_booking_dates', kwargs={'pk': self.booking.id})
        
    def test_edit_booking_dates_view_GET(self):
        """Test that the edit dates view loads correctly"""
        response = self.client.get(self.edit_dates_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'edit_booking_dates.html')
        self.assertContains(response, 'Editar Fechas de la Reserva')
    
    def test_edit_booking_dates_valid_POST(self):
        """Test that the edit dates view loads correctly"""
        new_checkin = self.today + timedelta(days=5)
        new_checkout = self.today + timedelta(days=7)
        
        response = self.client.post(self.edit_dates_url, {
            'checkin': new_checkin,
            'checkout': new_checkout
        })
        
        # Test redirect
        self.assertEqual(response.status_code, 302)
        
        # Update object from database
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.checkin, new_checkin)
        self.assertEqual(self.booking.checkout, new_checkout)
    
    def test_edit_booking_dates_invalid_dates(self):
        """Test that the edit dates view loads correctly"""
        response = self.client.post(self.edit_dates_url, {
            'checkin': self.tomorrow,
            'checkout': self.today  # Date of checkout before the date of checkin
        }, follow=True)  # Added follow=True to follow the redirect
        
        # Verify that the error message is displayed
        self.assertContains(response, 'La fecha de salida debe ser posterior a la fecha de entrada.')

    # Test that the edit dates view loads correctly
    def test_edit_booking_dates_occupied_dates(self):
        """Test that the edit dates view loads correctly"""
        # Create a new reservation that occupies the dates from 5 to 7
        occupied_checkin = self.today + timedelta(days=5)
        occupied_checkout = self.today + timedelta(days=7)
    
        # Create a reservation that occupies that range
        Booking.objects.create(
            room=self.room,  # Same room as the reservation we are editing
            customer=self.customer,
            checkin=occupied_checkin,
            checkout=occupied_checkout,
            guests=1,
            total=30.00,
            code='OCCUPIED1',
            state='NEW'
        )
    
        # Try to edit the original reservation to overlap with the occupied one
        response = self.client.post(
            self.edit_dates_url,
            {
                'checkin': occupied_checkin - timedelta(days=1),  # One day before
                'checkout': occupied_checkin + timedelta(days=1)  # Overlaps one day
            },
            follow=True  # Follow the redirect
        )
    
        # Verify that the error message is displayed
        self.assertContains(
            response, 
            'No hay disponibilidad para las fechas seleccionadas',
            msg_prefix="Debería mostrar mensaje de no disponibilidad"
        )
    
        # Verify that the reservation was not updated
        self.booking.refresh_from_db()
        self.assertNotEqual(self.booking.checkin, occupied_checkin - timedelta(days=1))
        self.assertNotEqual(self.booking.checkout, occupied_checkin + timedelta(days=1))
    
        # Verify that it remains on the same page (code 200) instead of redirecting
        self.assertEqual(response.status_code, 200)

        
        

