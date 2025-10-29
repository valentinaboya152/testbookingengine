from django.test import TestCase, Client, override_settings
from django.urls import reverse
from .models import Room, Room_type

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


