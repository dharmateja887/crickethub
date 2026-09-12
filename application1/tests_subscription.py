from django.test import TestCase
from django.urls import reverse


class SubscriptionViewTests(TestCase):
    def test_subscription_page_renders(self):
        response = self.client.get(reverse('subscription'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Subscription')

    def test_subscription_page_shows_razorpay_key(self):
        response = self.client.get(reverse('subscription'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'checkout.razorpay.com')

    def test_order_endpoint_requires_plan(self):
        response = self.client.post(
            reverse('create_subscription_order'),
            data={},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_subscription_requires_payment_details(self):
        response = self.client.post(
            reverse('subscription'),
            data={'plan_name': 'Premium Plan', 'price': 199},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)