from django.test import TestCase

from .models import ChatMessage, Profile, Subscription


class ModelTests(TestCase):
    def test_profile_can_be_created(self):
        profile = Profile.objects.create(
            full_name="MS Dhoni",
            email="dhoni@crickethub.com",
            mobile="9876543210",
        )
        self.assertEqual(profile.full_name, "MS Dhoni")
        self.assertEqual(profile.email, "dhoni@crickethub.com")
        self.assertEqual(str(profile), "MS Dhoni")

    def test_subscription_can_be_created(self):
        sub = Subscription.objects.create(
            plan_name="Premium Plan",
            price=199,
            transaction_id="pay_test_123",
        )
        self.assertEqual(sub.price, 199)
        self.assertEqual(sub.status, "active")
        self.assertIn("Premium", str(sub))

    def test_chat_message_can_be_created(self):
        msg = ChatMessage.objects.create(message="Hello CricketHub", is_user=True)
        self.assertTrue(msg.is_user)
        self.assertFalse(msg.is_chatbox)
        self.assertIn("Hello", str(msg))