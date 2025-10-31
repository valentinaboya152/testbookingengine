from django.test import TestCase, Client, override_settings
from django.urls import reverse
from .models import Room, Booking, Room_type
from datetime import date, timedelta

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