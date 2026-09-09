from django.test import TestCase
from django.urls import reverse


class SubscriptionViewTests(TestCase):
    def test_subscription_page_renders(self):
        response = self.client.get(reverse('Subscription'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Subscription Plans')

    def test_subscription_page_accepts_plan_selection(self):
        response = self.client.post(reverse('Subscription'), {'plan': 'Premium Plan'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session['selected_plan'], 'Premium Plan')
