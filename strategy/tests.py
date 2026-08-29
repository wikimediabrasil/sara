from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from strategy.models import (
    Direction,
    EvaluationObjective,
    LearningArea,
    StrategicAxis,
    StrategicLearningQuestion,
)


class DirectionModelTests(TestCase):
    def setUp(self):
        self.strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")

    def test_direction_str_returns_its_text(self):
        direction = Direction.objects.create(
            text="Direction", strategic_axis=self.strategic_axis
        )
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


class LearningAreaModelTest(TestCase):
    def setUp(self):
        self.learning_area_text = "Test Learning Area"
        self.learning_area = LearningArea.objects.create(text=self.learning_area_text)

    def test_learning_area_str_method_returns_its_text(self):
        self.assertEqual(str(self.learning_area), self.learning_area_text)

    def test_learning_area_clean_method(self):
        learning_area = LearningArea()
        with self.assertRaises(ValidationError):
            learning_area.clean()


class StrategicLearningQuestionModelTest(TestCase):
    def setUp(self):
        self.learning_area = LearningArea.objects.create(text="Learning Area")
        self.strategic_question_text = "Strategic Learning Question"
        self.strategic_question = StrategicLearningQuestion.objects.create(
            text=self.strategic_question_text, learning_area=self.learning_area
        )

    def test_strategic_learning_question_str_method_returns_its_text(self):
        self.assertEqual(str(self.strategic_question), self.strategic_question_text)

    def test_strategic_learning_question_learning_area(self):
        self.assertEqual(self.strategic_question.learning_area, self.learning_area)

    def test_strategic_learning_question_clean_method(self):
        strategic_learning_question = StrategicLearningQuestion()
        with self.assertRaises(ValidationError):
            strategic_learning_question.clean()


class EvaluationObjectiveModelTest(TestCase):
    def setUp(self):
        self.learning_area = LearningArea.objects.create(text="Test Learning Area")
        self.evaluation_objective_text = "Test Evaluation Objective"
        self.evaluation_objective = EvaluationObjective.objects.create(
            text=self.evaluation_objective_text, learning_area=self.learning_area
        )

    def test_evaluation_objective_str_method_returns_its_text(self):
        self.assertEqual(str(self.evaluation_objective), self.evaluation_objective_text)

    def test_evaluation_objective_learning_area(self):
        self.assertEqual(self.evaluation_objective.learning_area, self.learning_area)

    def test_evaluation_objective_clean_method(self):
        evaluation_objective = EvaluationObjective()
        with self.assertRaises(ValidationError):
            evaluation_objective.clean()
