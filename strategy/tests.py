from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import StrategicAxis, Direction
from django.urls import reverse

class DirectionModelTests(TestCase):
    def setUp(self):
        self.strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")

    def test_direction_str_returns_its_text(self):
        direction = Direction.objects.create(text="Direction", strategic_axis=self.strategic_axis)
        self.assertEqual(str(direction), "Direction")

    def test_direction_cannot_have_empty_text(self):
        with self.assertRaises(ValidationError):
            direction = Direction(text="", strategic_axis=self.strategic_axis)
            direction.full_clean()


class StrategicAxisModelTests(TestCase):
    def setUp(self):
        self.strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")

    def test_strategic_axis_str_returns_its_text(self):
        self.assertEqual(str(self.strategic_axis), "Strategic Axis")

    def test_strategic_axis_cannot_have_empty_text(self):
        with self.assertRaises(ValidationError):
            axis = StrategicAxis(text="")
            axis.full_clean()


class StrategicAxisViewTests(TestCase):
    def setUp(self):
        self.strategic_axis1 = StrategicAxis.objects.create(text="Strategic Axis 1")
        self.strategic_axis2 = StrategicAxis.objects.create(text="Strategic Axis 2")

    def test_show_strategy_view(self):
        response = self.client.get(reverse("strategy:show_strategy"))
        self.assertEqual(response.status_code, 302)
