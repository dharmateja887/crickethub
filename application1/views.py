import json
import logging
import random
import re
from datetime import date

import razorpay

from google import genai
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import ChatMessage, Profile, Subscription
from dashboard.models import DashboardChatMessage, DashboardSuggestion
from CricketZone.settings import GOOGLE_API_KEY, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

_genai_client = None


def get_genai_client():
    global _genai_client
    if _genai_client is None:
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not configured.")
        _genai_client = genai.Client(api_key=GOOGLE_API_KEY)
    return _genai_client

logger = logging.getLogger(__name__)


def strip_html(text):
    return re.sub(r'<[^>]+>', '', text)


def index(request):
    return render(request, 'application2/index.html')


def chatbox(request):
    if request.method == 'POST':
        if request.headers.get('content-type') == 'application/json':
            try:
                body_data = json.loads(request.body)
            except json.JSONDecodeError:
                body_data = {}
            if body_data.get('clear_history'):
                if request.user.is_authenticated:
                    ChatMessage.objects.filter(user=request.user, is_chatbox=True).delete()
                    DashboardChatMessage.objects.filter(user=request.user, is_chatbox=True).delete()
                else:
                    request.session['guest_chatbox_history'] = []
                    request.session.modified = True
                return JsonResponse({'success': True})

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST
        original = str(data.get('question', '')).strip()
        question_lower = original.lower()

        if not question_lower:
            return JsonResponse({'answer': 'Please type a question.'})

        response = None
        ai_error = None
        sys_prompt = (
            "You are CricketHub Chatbox Assistant. Answer ANY question the user asks. "
            "You can help with: cricket rules, player stats, tournament history, match schedules, "
            "CricketHub features, subscriptions (Male Only ₹99/mo, Female Only ₹99/mo, Premium ₹199/mo), "
            "registration, login, profiles, payments, live streaming, and general knowledge. "
            "Keep answers concise and friendly. Use HTML formatting when helpful. "
            "If the user says hi/hello, welcome them warmly."
        )
        for model_name in ('gemini-3.6-flash', 'gemini-3.5-flash'):
            if response:
                break
            try:
                interaction = get_genai_client().interactions.create(
                    model=model_name,
                    input=[
                        {"type": "text", "text": f"{sys_prompt}\n\nUser question: {original}"},
                    ],
                )
                if interaction.output_text:
                    response = interaction.output_text.strip()
            except Exception as e:
                ai_error = str(e)
                logger.error("Gemini chatbox error (%s): %s", model_name, ai_error)

        if not response:
            def chip(text, q=None):
                q = q or text
                return f'<button class="chat-chip" onclick="askQuick(\'{q}\')">{text}</button>'

            format_chips = ' '.join([
                chip('🏏 ODI', 'show ODI games'),
                chip('🏏 Test', 'show Test games'),
                chip('🏏 T20', 'show T20 games'),
                chip('🏏 Under-19', 'show Under-19 games'),
                chip('🏏 Under Angitropy', 'show Under Angitropy games'),
            ])

            answers = {
                'hi': f"👋 Welcome to CricketHub! 🎉<br><br>I can answer any question you have. Try asking about cricket, tournaments, or the platform!",
                'hello': f"👋 Welcome to CricketHub! 🎉<br><br>I can answer any question you have. Try asking about cricket, tournaments, or the platform!",
                'hey': f"👋 Welcome to CricketHub! 🎉<br><br>I can answer any question you have. Try asking about cricket, tournaments, or the platform!",
                'subscription': (
                    "We offer three plans: <strong>Male Only</strong> (₹99/mo) for men's cricket, "
                    "<strong>Female Only</strong> (₹99/mo) for women's cricket, and <strong>Premium</strong> (₹199/mo) for all matches. "
                    "You can subscribe from the Subscription page in the sidebar."
                ),
                'premium': (
                    "The <strong>Premium</strong> plan costs <strong>₹199/month</strong> and gives you access to all men's and women's "
                    "cricket tournaments, live scores, multi-screen streaming, and more. "
                    "It's our most popular choice!"
                ),
                'price': "Our plans: <strong>Male Only</strong> ₹99/mo, <strong>Female Only</strong> ₹99/mo, <strong>Premium</strong> ₹199/mo. All give you access to live streaming and scores.",
                'register': "You can register using your 10-digit mobile number. A verification OTP will be sent, and you'll be logged in automatically.",
                'login': "Login using your registered mobile number. If you don't have an account, you can register from the sidebar.",
                'help': (
                    "I'm CricketHub Chatbox! I can answer questions about:<br>"
                    "• <strong>Cricket</strong> — rules, players, history<br>"
                    "• <strong>Subscriptions</strong> — plans, pricing, payment<br>"
                    "• <strong>Games</strong> — all cricket formats and tournaments<br>"
                    "• <strong>Profile</strong> — editing your info<br>"
                    "• <strong>Registration / Login</strong> — account help<br>"
                    "• <strong>General knowledge</strong> — anything you ask!"
                ),
            }

            for keyword, answer in sorted(answers.items(), key=lambda x: -len(x[0])):
                if keyword in question_lower:
                    response = answer
                    break

            if not response:
                response = (
                    "🤖 <strong>AI assistant is currently unavailable</strong> (rate limit reached). "
                    "Please try again in a moment.<br><br>"
                    "Meanwhile, try asking about:<br>"
                    "• <strong>Cricket games</strong> — see all formats<br>"
                    "• <strong>Subscriptions</strong> — plans & pricing<br>"
                    "• <strong>Tournaments</strong> — ODI, Test, T20, U19<br>"
                    "• <strong>Profile / Registration</strong><br><br>"
                    f'Or just say <strong>"hi"</strong> to explore cricket games!'
                )

        if request.user.is_authenticated:
            ChatMessage.objects.create(user=request.user, message=original, is_user=True, is_chatbox=True)
            ChatMessage.objects.create(user=request.user, message=strip_html(response), is_user=False, is_chatbox=True)
            DashboardChatMessage.objects.create(user=request.user, message=original, is_user=True, is_chatbox=True)
            DashboardChatMessage.objects.create(user=request.user, message=strip_html(response), is_user=False, is_chatbox=True)
        else:
            if 'guest_chatbox_history' not in request.session:
                request.session['guest_chatbox_history'] = []
            request.session['guest_chatbox_history'].append({'message': original, 'is_user': True})
            request.session['guest_chatbox_history'].append({'message': strip_html(response), 'is_user': False})
            request.session.modified = True

        return JsonResponse({'answer': response})

    chat_history = []
    if request.user.is_authenticated:
        messages = ChatMessage.objects.filter(user=request.user, is_chatbox=True)[:100]
        chat_history = [
            {'message': m.message, 'is_user': m.is_user, 'id': m.id}
            for m in messages
        ]
    else:
        chat_history = request.session.get('guest_chatbox_history', [])[-100:]

    return render(request, 'application2/chatbox.html', {
        'chat_history_json': json.dumps(chat_history),
    })


def suggestions(request):
    if request.method == 'POST':
        if request.headers.get('content-type') == 'application/json':
            try:
                body_data = json.loads(request.body)
            except json.JSONDecodeError:
                body_data = {}
            if body_data.get('clear_history'):
                if request.user.is_authenticated:
                    ChatMessage.objects.filter(user=request.user, is_chatbox=False).delete()
                    DashboardSuggestion.objects.filter(user=request.user).delete()
                else:
                    request.session['guest_suggestion_history'] = []
                    request.session.modified = True
                return JsonResponse({'success': True})

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST
        original = str(data.get('question', '')).strip()
        question_lower = original.lower()

        if not question_lower:
            return JsonResponse({'answer': 'Please type a question.'})

        response = None
        ai_error = None
        sys_prompt = (
            "You are CricketHub Assistant, a helpful AI for a cricket website. "
            "Answer questions about: cricket tournaments (ODI, Test, T20, Under-19, Under Angitropy), "
            "subscription plans (Male Only ₹99/mo, Female Only ₹99/mo, Premium ₹199/mo), "
            "user profiles, registration, login, payments, live streaming, and anything else about CricketHub. "
            "Keep answers concise and friendly. Use HTML formatting when helpful. "
            "If the user says hi/hello, welcome them and mention CricketHub's cricket games. "
            "If they are not asking about CricketHub or cricket, politely redirect to CricketHub topics."
        )
        for model_name in ('gemini-3.6-flash', 'gemini-3.5-flash'):
            if response:
                break
            try:
                interaction = get_genai_client().interactions.create(
                    model=model_name,
                    input=[
                        {"type": "text", "text": f"{sys_prompt}\n\nUser question: {original}"},
                    ],
                )
                if interaction.output_text:
                    response = interaction.output_text.strip()
            except Exception as e:
                ai_error = str(e)
                logger.error("Gemini suggestions error (%s): %s", model_name, ai_error)

        if not response:
            def chip(text, q=None):
                q = q or text
                return f'<button class="chat-chip" onclick="askQuick(\'{q}\')">{text}</button>'

            format_chips = ' '.join([
                chip('🏏 ODI', 'show ODI games'),
                chip('🏏 Test', 'show Test games'),
                chip('🏏 T20', 'show T20 games'),
                chip('🏏 Under-19', 'show Under-19 games'),
                chip('🏏 Under Angitropy', 'show Under Angitropy games'),
            ])

            answers = {
                'hi': (
                    "👋 Welcome to CricketHub games! 🎉<br><br>"
                    "Explore our cricket formats below. Click any to see the tournaments available:<br><br>"
                    f'<div class="chip-group">{format_chips}</div><br>'
                    "Or ask me anything about subscriptions, your profile, registration, and more!"
                ),
                'hello': (
                    "👋 Welcome to CricketHub games! 🎉<br><br>"
                    "Explore our cricket formats below. Click any to see the tournaments available:<br><br>"
                    f'<div class="chip-group">{format_chips}</div><br>'
                    "Or ask me anything about subscriptions, your profile, registration, and more!"
                ),
                'hey': (
                    "👋 Welcome to CricketHub games! 🎉<br><br>"
                    "Explore our cricket formats below. Click any to see the tournaments available:<br><br>"
                    f'<div class="chip-group">{format_chips}</div><br>'
                    "Or ask me anything about subscriptions, your profile, registration, and more!"
                ),
                'subscription': (
                    "We offer three plans: <strong>Male Only</strong> (₹99/mo) for men's cricket, "
                    "<strong>Female Only</strong> (₹99/mo) for women's cricket, and <strong>Premium</strong> (₹199/mo) for all matches. "
                    "You can subscribe from the Subscription page in the sidebar."
                ),
                'premium': (
                    "The <strong>Premium</strong> plan costs <strong>₹199/month</strong> and gives you access to all men's and women's "
                    "cricket tournaments, live scores, multi-screen streaming, and more. "
                    "It's our most popular choice!"
                ),
                'male': (
                    "The <strong>Male Only</strong> plan (₹99/mo) covers all men's T20 leagues, ODI series, "
                    "Test matches, and live scores. Upgrade to Premium for women's cricket too."
                ),
                'female': (
                    "The <strong>Female Only</strong> plan (₹99/mo) gives you access to all women's T20 leagues, "
                    "ODI series, Test matches, and live scores. Upgrade to Premium for men's cricket too."
                ),
                'tournament': (
                    "We host several tournament formats. Click any to explore:<br><br>"
                    f'<div class="chip-group">{format_chips}</div><br>'
                    "Each has men's and women's categories. Visit the Tournaments page too!"
                ),
                'odi': (
                    "<strong>🏏 ODI (One Day International)</strong> — 50-over format with big innings and dramatic finishes.<br><br>"
                    "Tournaments we feature:<br>"
                    f'{chr(10).join(chip(t) for t in ["World Cup ODI", "Champions Trophy", "Asia Cup ODI", "Tri-Series ODI", "Bilateral ODI", "ICC ODI League", "ODI Night Series", "ODI Finals Cup", "Super ODI", "ODI Clash of Titans"])}'
                ),
                'test': (
                    "<strong>🏏 Test Cricket</strong> — The classic 5-day format where patience and strategy decide the winner.<br><br>"
                    "Tournaments we feature:<br>"
                    f'{chr(10).join(chip(t) for t in ["Ashes Test", "World Test Championship", "Border-Gavaskar Trophy", "Pakistan vs England", "South Africa Test Series", "India Test Cup", "Day-Night Test", "Test Final Challenge", "Historic Test Rivalry", "Test Masters Cup"])}'
                ),
                't20': (
                    "<strong>🏏 T20 Cricket</strong> — Fast 20-over format built for explosive batting and last-over thrillers.<br><br>"
                    "Tournaments we feature:<br>"
                    f'{chr(10).join(chip(t) for t in ["IPL T20", "T20 World Cup", "Big Bash", "PSL T20", "CPL T20", "T20 Smash", "Super T20 Cup", "Night T20 League", "T20 Finals Showdown", "Rapid T20 Challenge"])}'
                ),
                'price': "Our plans: <strong>Male Only</strong> ₹99/mo, <strong>Female Only</strong> ₹99/mo, <strong>Premium</strong> ₹199/mo. All give you access to live streaming and scores.",
                'cost': "Our plans: <strong>Male Only</strong> ₹99/mo, <strong>Female Only</strong> ₹99/mo, <strong>Premium</strong> ₹199/mo. All give you access to live streaming and scores.",
                'profile': "Your profile stores your name, email, mobile, date of birth, gender, location, about section, and avatar. You can update it anytime from the Profile page.",
                'sidebar': "The sidebar gives you quick access to Home, Tournaments, Profile, Subscription, Suggestions, and more. Your profile avatar and plan info show at the bottom.",
                'live': "Live streaming is available for all matches depending on your subscription plan. Upgrade to Premium for full access to multi-screen streaming.",
                'register': "You can register using your 10-digit mobile number. A verification OTP will be sent, and you'll be logged in automatically.",
                'login': "Login using your registered mobile number. If you don't have an account, you can register from the sidebar.",
                'logout': "You can log out using the Logout button at the bottom of the sidebar. Your data is always saved in the database.",
                'payment': "We accept card payments and UPI. During checkout, you can enter your card details or UPI ID to complete your subscription purchase.",
                'women': "Women's cricket includes T20 leagues, ODI series, Test matches, and more. The Female Only plan (₹99/mo) covers all women's content.",
                'men': "Men's cricket includes T20 leagues, ODI series, Test matches, and more. The Male Only plan (₹99/mo) covers all men's content.",
                'games': (
                    "🏏 <strong>Cricket Games on CricketHub</strong><br><br>"
                    "We offer several exciting formats. Click any to see the specific tournaments:<br><br>"
                    f'<div class="chip-group">{format_chips}</div>'
                ),
                'cricket': (
                    "🏏 <strong>Cricket Games on CricketHub</strong><br><br>"
                    "We offer several exciting formats. Click any to see the specific tournaments:<br><br>"
                    f'<div class="chip-group">{format_chips}</div>'
                ),
                'help': (
                    "I'm CricketHub Assistant! I can answer questions about:<br>"
                    "• <strong>Subscriptions</strong> — plans, pricing, payment<br>"
                    "• <strong>Games</strong> — all cricket formats and tournaments<br>"
                    "• <strong>Tournaments</strong> — ODI, Test, T20, U19 and more<br>"
                    "• <strong>Profile</strong> — editing your info<br>"
                    "• <strong>Registration / Login</strong> — account help<br><br>"
                    "Just ask or type <strong>\"hi\"</strong> to see cricket games!"
                ),
            }

            for keyword, answer in sorted(answers.items(), key=lambda x: -len(x[0])):
                if keyword in question_lower:
                    response = answer
                    break

            if not response:
                response = (
                    "🤖 <strong>AI assistant is currently unavailable</strong> (rate limit reached). "
                    "Please try again in a moment.<br><br>"
                    "Meanwhile, try asking about:<br>"
                    "• <strong>Cricket games</strong> — see all formats<br>"
                    "• <strong>Subscriptions</strong> — plans & pricing<br>"
                    "• <strong>Tournaments</strong> — ODI, Test, T20, U19<br>"
                    "• <strong>Profile / Registration</strong><br><br>"
                    f'Or just say <strong>"hi"</strong> to explore cricket games!'
                )

        if request.user.is_authenticated:
            ChatMessage.objects.create(user=request.user, message=original, is_user=True, is_chatbox=False)
            ChatMessage.objects.create(user=request.user, message=response, is_user=False, is_chatbox=False)
            DashboardSuggestion.objects.create(user=request.user, question=original, response=strip_html(response))
        else:
            if 'guest_suggestion_history' not in request.session:
                request.session['guest_suggestion_history'] = []
            request.session['guest_suggestion_history'].append({'message': original, 'is_user': True})
            request.session['guest_suggestion_history'].append({'message': response, 'is_user': False})
            request.session.modified = True

        return JsonResponse({'answer': response})

    chat_history = []
    if request.user.is_authenticated:
        messages = ChatMessage.objects.filter(user=request.user, is_chatbox=False)[:100]
        chat_history = [
            {'message': m.message, 'is_user': m.is_user, 'id': m.id}
            for m in messages
        ]
    else:
        chat_history = request.session.get('guest_suggestion_history', [])[-100:]

    return render(request, 'application2/suggestions.html', {
        'chat_history_json': json.dumps(chat_history),
    })


def subscription(request):
    profile_obj = None
    if request.user.is_authenticated:
        profile_obj = Profile.objects.filter(user=request.user).order_by('-id').first()

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST

        plan_name = str(data.get('plan_name', '') or '').strip()
        raw_price = data.get('price')
        try:
            price = int(raw_price)
        except (TypeError, ValueError):
            price = 0
        if not plan_name or not price:
            return JsonResponse({'error': 'Missing plan_name or price'}, status=400)

        payment_id = str(data.get('razorpay_payment_id', '') or '').strip()
        order_id = str(data.get('razorpay_order_id', '') or '').strip()
        signature = str(data.get('razorpay_signature', '') or '').strip()
        if not (payment_id and order_id and signature):
            return JsonResponse({'error': 'Missing payment details'}, status=400)

        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature,
            })
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'error': 'Payment signature verification failed'}, status=400)

        sub = Subscription(
            user=request.user if request.user.is_authenticated else None,
            plan_name=plan_name,
            price=price,
            payment_method=data.get('payment_method', 'razorpay'),
            transaction_id=payment_id,
        )
        sub.save()
        return JsonResponse({'success': True})

    current_subscription = None
    if request.user.is_authenticated:
        current_subscription = Subscription.objects.filter(user=request.user).order_by('-id').first()

    return render(request, 'application2/Subscription.html', {
        'current_profile': profile_obj,
        'current_subscription': current_subscription,
        'razorpay_key_id': RAZORPAY_KEY_ID,
    })


def create_subscription_order(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    if not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET):
        return JsonResponse({'error': 'Razorpay is not configured on the server'}, status=503)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    plan_name = str(data.get('plan_name', '') or '').strip()
    raw_price = data.get('price')
    try:
        price = int(raw_price)
    except (TypeError, ValueError):
        price = 0
    if not plan_name or not price:
        return JsonResponse({'error': 'Missing plan_name or price'}, status=400)

    try:
        order = razorpay_client.order.create({
            'amount': price * 100,
            'currency': 'INR',
            'receipt': f'sub_{plan_name}_{price}',
            'payment_capture': 1,
        })
    except razorpay.errors.BadRequestError as e:
        return JsonResponse({'error': f'Payment setup failed: {e}'}, status=400)
    except razorpay.errors.SignatureVerificationError as e:
        return JsonResponse({'error': 'Payment verification failed'}, status=400)
    except Exception as e:
        logger.error('Razorpay order creation failed: %s', e)
        return JsonResponse({'error': 'Payment service unavailable. Please try again.'}, status=502)

    return JsonResponse({
        'order_id': order['id'],
        'amount': order['amount'],
        'currency': order['currency'],
        'key_id': RAZORPAY_KEY_ID,
        'plan_name': plan_name,
        'plan_price': price,
    })


def tournaments(request):
    tournaments = [
        {
            'title': 'ODI',
            'subtitle': 'One Day International',
            'description': 'High-paced 50-over matches with big innings and dramatic finishes.',
            'badge': 'ODI',
            'slug': 'odi',
        },
        {
            'title': 'Test',
            'subtitle': 'Classic red-ball cricket',
            'description': 'Five-day battles where patience, skill, and strategy decide the winner.',
            'badge': 'TEST',
            'slug': 'test',
        },
        {
            'title': 'T20',
            'subtitle': 'Fast and fearless',
            'description': 'Short, explosive games made for power hitting and last-over thrillers.',
            'badge': 'T20',
            'slug': 't20',
        },
        {
            'title': 'Under 19',
            'subtitle': 'Future stars',
            'description': 'Watch the next generation of cricketing talent showcase their talent.',
            'badge': 'U19',
            'slug': 'under19',
        },
        {
            'title': 'Under Angitropy',
            'subtitle': 'Special league',
            'description': 'A unique showcase tournament built around elite young cricketing talent.',
            'badge': 'SPECIAL',
            'slug': 'underangitropy',
        },
    ]

    categories = [
        {
            'title': 'Men Cricket',
            'description': 'Explore elite male cricket competitions and matchups.',
            'url': '/tournaments/men-cricket/',
        },
        {
            'title': 'Women Cricket',
            'description': 'Discover top women\'s cricket tournaments and rising stars.',
            'url': '/tournaments/women-cricket/',
        },
    ]

    current_subscription = None
    if request.user.is_authenticated:
        current_subscription = Subscription.objects.filter(user=request.user).order_by('-id').first()

    return render(request, 'application2/tournaments.html', {
        'tournaments': tournaments,
        'categories': categories,
        'current_subscription': current_subscription,
    })


def tournament_detail(request, slug):
    data = {
        'odi': {
            'title': 'ODI Tournament',
            'description': 'Experience the excitement of One Day International cricket with high-pressure innings and dramatic endings.',
            'items': [
                {'title': 'World Cup ODI', 'description': 'Top nations battle for the coveted world title.'},
                {'title': 'Champions Trophy', 'description': 'Elite teams compete in a fast-paced 50-over showdown.'},
                {'title': 'Asia Cup ODI', 'description': 'A regional tournament filled with intense rivalry.'},
                {'title': 'Tri-Series ODI', 'description': 'Balanced contests with multiple top teams in action.'},
                {'title': 'Bilateral ODI', 'description': 'Head-to-head series full of momentum swings.'},
                {'title': 'ICC ODI League', 'description': 'A long-form pathway to global cricket glory.'},
                {'title': 'ODI Night Series', 'description': 'Thrilling evening matches under lights.'},
                {'title': 'ODI Finals Cup', 'description': 'The best of the best clash for the championship.'},
                {'title': 'Super ODI', 'description': 'High-scoring games with explosive batting.'},
                {'title': 'ODI Clash of Titans', 'description': 'Historic rivalries in a one-day format.'},
            ],
        },
        'test': {
            'title': 'Test Tournament',
            'description': 'Step into the longest format where endurance, skill, and strategy are tested over five days.',
            'items': [
                {'title': 'Ashes Test', 'description': 'Historic rivalry packed with pressure and pride.'},
                {'title': 'World Test Championship', 'description': 'The ultimate test of consistency across the longest format.'},
                {'title': 'Border-Gavaskar Trophy', 'description': 'A fierce battle between two cricketing giants.'},
                {'title': 'Pakistan vs England', 'description': 'Classic red-ball tension and strong bowling battles.'},
                {'title': 'South Africa Test Series', 'description': 'High-quality pace and resilience on display.'},
                {'title': 'India Test Cup', 'description': 'A platform for top teams to prove their mettle.'},
                {'title': 'Day-Night Test', 'description': 'A modern twist on the classic format.'},
                {'title': 'Test Final Challenge', 'description': 'A decisive finale brimming with drama.'},
                {'title': 'Historic Test Rivalry', 'description': 'Classic matchups that stand the test of time.'},
                {'title': 'Test Masters Cup', 'description': 'A premium tournament for elite red-ball cricket.'},
            ],
        },
        't20': {
            'title': 'T20 Tournament',
            'description': 'Watch fast-moving T20 cricket where every ball can change the match in an instant.',
            'items': [
                {'title': 'IPL T20', 'description': 'The biggest cricket carnival with star-studded teams.'},
                {'title': 'T20 World Cup', 'description': 'Global power-hitting and elite bowling in one stage.'},
                {'title': 'Big Bash', 'description': 'Australia\'s festive cricket festival with flair and pace.'},
                {'title': 'PSL T20', 'description': 'A passionate league with explosive matchups.'},
                {'title': 'CPL T20', 'description': 'Caribbean fireworks and high-energy cricket.'},
                {'title': 'T20 Smash', 'description': 'Short and sharp games that reward smart aggression.'},
                {'title': 'Super T20 Cup', 'description': 'Battle royale for the best T20 teams.'},
                {'title': 'Night T20 League', 'description': 'The thrill of big hits under floodlights.'},
                {'title': 'T20 Finals Showdown', 'description': 'The grand finale for the most entertaining format.'},
                {'title': 'Rapid T20 Challenge', 'description': 'Fast-paced cricket built for nonstop excitement.'},
            ],
        },
        'under19': {
            'title': 'Under 19 Tournament',
            'description': 'A stage for future stars to display technique, confidence, and fearless cricket.',
            'items': [
                {'title': 'U19 World Cup', 'description': 'The brightest junior talent competes on a global stage.'},
                {'title': 'Asia U19 Cup', 'description': 'Young players from across Asia go head-to-head.'},
                {'title': 'Future Stars League', 'description': 'An emerging platform for next-gen cricketers.'},
                {'title': 'Junior Test Series', 'description': 'A long-format experience for young red-ball prospects.'},
                {'title': 'U19 IQ Challenge', 'description': 'A smart and skillful showcase of junior cricket.'},
                {'title': 'Youth ODI Trophy', 'description': 'A polished one-day competition for future stars.'},
                {'title': 'Talent Hunt Cup', 'description': 'The next generation steps up in a high-pressure tournament.'},
                {'title': 'Under 19 Finals', 'description': 'The most promising juniors clash for the crown.'},
                {'title': 'Spin & Pace Cup', 'description': 'A balanced contest between young bowlers and batsmen.'},
                {'title': 'Junior Champions League', 'description': 'A tournament built around elite youth teams.'},
            ],
        },
        'underangitropy': {
            'title': 'Under Angitropy Tournament',
            'description': 'A special showcase tournament designed to spotlight exceptional emerging talent.',
            'items': [
                {'title': 'Angitropy Cup', 'description': 'A showcase for rising cricketers with big potential.'},
                {'title': 'Elite Youth Series', 'description': 'A high-quality competition for the most promising juniors.'},
                {'title': 'Future Champions', 'description': 'A tournament centered on talent, discipline, and hunger.'},
                {'title': 'Rising Stars Open', 'description': 'An invitation-only platform for standout young players.'},
                {'title': 'Powerplay Challenge', 'description': 'A special event focused on aggressive early-match play.'},
                {'title': 'Prospect Finals', 'description': 'The best emerging players face off for the title.'},
                {'title': 'Skill Sprint Cup', 'description': 'A fast-paced format testing all-round talent.'},
                {'title': 'NextGen Invitational', 'description': 'An elite junior competition with top-tier exposure.'},
                {'title': 'Storm Cup', 'description': 'A fierce display of talent under pressure.'},
                {'title': 'Talent Trophy', 'description': 'A special finale celebrating standout performances.'},
            ],
        },
        'men-cricket': {
            'title': 'Men Cricket',
            'description': 'A dedicated collection of men\'s cricket competitions featuring top teams and legendary rivalries.',
            'items': [
                {'title': 'India Men', 'description': 'A powerhouse team known for flair and depth.'},
                {'title': 'Australia Men', 'description': 'A fierce side with elite pace and strong character.'},
                {'title': 'England Men', 'description': 'Classic cricketing identity and modern aggressive intent.'},
                {'title': 'South Africa Men', 'description': 'World-class pace and fearless cricket.'},
                {'title': 'Pakistan Men', 'description': 'Dynamic, talented, and always dangerous in big moments.'},
                {'title': 'New Zealand Men', 'description': 'Clinical, disciplined, and consistently competitive.'},
                {'title': 'Sri Lanka Men', 'description': 'Skilled spin and clever all-round performances.'},
                {'title': 'West Indies Men', 'description': 'Electric batting and historic swagger.'},
                {'title': 'Bangladesh Men', 'description': 'Rapid progress and dangerous match-winners.'},
                {'title': 'Afghanistan Men', 'description': 'A rising force with fearless talent.'},
            ],
        },
        'women-cricket': {
            'title': 'Women Cricket',
            'description': 'A dedicated collection of women\'s cricket competitions celebrating elite talent and growth.',
            'items': [
                {'title': 'Australia Women', 'description': 'A dominant side with elite batters and bowlers.'},
                {'title': 'England Women', 'description': 'World-class skill and modern tactical strength.'},
                {'title': 'India Women', 'description': 'Dynamic and exciting with strong all-round depth.'},
                {'title': 'South Africa Women', 'description': 'Fast, skilled, and full of confidence.'},
                {'title': 'New Zealand Women', 'description': 'Clinical and composed under pressure.'},
                {'title': 'Pakistan Women', 'description': 'A talent-rich team with exciting young stars.'},
                {'title': 'West Indies Women', 'description': 'Powerful batting and fearless play.'},
                {'title': 'Sri Lanka Women', 'description': 'Graceful spin and smart game awareness.'},
                {'title': 'Bangladesh Women', 'description': 'Improving quickly with growing confidence.'},
                {'title': 'Ireland Women', 'description': 'A spirited team known for resilience and heart.'},
            ],
        },
    }

    selected = data.get(slug, data['odi'])
    return render(request, 'application2/tournament_detail.html', {
        'title': selected['title'],
        'description': selected['description'],
        'items': selected['items'],
    })


GAMES = [
    {
        'slug': 'ipl-2026',
        'title': 'IPL Cricket 2026',
        'image': 'game11.jpg',
        'tagline': 'Play exciting IPL matches with your favourite teams and compete for the trophy.',
        'description': 'T20 • Sports • Multiplayer',
        'format': 'T20',
        'embed_url': 'https://www.crazygames.com/embed/cricket-superstar-league',
        'embed_provider': 'CrazyGames',
    },
    {
        'slug': 'world-cricket-championship',
        'title': 'World Cricket Championship',
        'image': 'game12.jpg',
        'tagline': 'Experience realistic cricket gameplay and become the world champion.',
        'description': 'Cricket • Tournament • Online',
        'format': 'ODI',
    },
    {
        'slug': 'super-over',
        'title': 'Super Over Cricket',
        'image': 'game13.jpg',
        'tagline': 'Hit sixes, chase targets and enjoy thrilling super over matches.',
        'description': 'Cricket • Arcade • Action',
        'format': 'T20',
        'embed_url': 'https://zv1y2i8p.play.gamezop.com/g/HJP4afkvqJQ',
        'embed_provider': 'Gamezop',
    },
    {
        'slug': 'street-cricket',
        'title': 'Street Cricket League',
        'image': 'game14.jpg',
        'tagline': 'Enjoy quick cricket matches and fun challenges with friends.',
        'description': 'Cricket • Casual • Fun',
        'format': 'T20',
        'embed_url': 'https://www.madkidgames.com/full/gully-cricket-game',
        'embed_provider': 'MadKidGames',
    },
    {
        'slug': 'cricket-league-3d',
        'title': 'Cricket League 3D',
        'image': 'game15.jpg',
        'tagline': 'Build your dream team and win league championships.',
        'description': 'Cricket • League • Multiplayer',
        'format': 'ODI',
        'embed_url': 'https://zv1y2i8p.play.gamezop.com/g/PRbBrRtjr',
        'embed_provider': 'Gamezop',
    },
    {
        'slug': 'power-hit',
        'title': 'Power Hit Cricket',
        'image': 'game21.jpg',
        'tagline': 'Smash sixes and dominate the scoreboard in fast-paced matches.',
        'description': 'Cricket • Power • Arcade',
        'format': 'T20',
    },
    {
        'slug': 'fast-bowling',
        'title': 'Fast Bowling Challenge',
        'image': 'game22.jpg',
        'tagline': 'Bowl with precision and outsmart every batsman in the arena.',
        'description': 'Cricket • Bowling • Skill',
        'format': 'Test',
    },
    {
        'slug': 'stadium-clash',
        'title': 'Stadium Clash',
        'image': 'game23.jpg',
        'tagline': 'Face thrilling rival teams in an intense cricket showdown.',
        'description': 'Cricket • Stadium • Competitive',
        'format': 'ODI',
    },
    {
        'slug': 'champion-cup',
        'title': 'Champion Cup',
        'image': 'game24.jpg',
        'tagline': 'Compete in tournament rounds and claim the ultimate crown.',
        'description': 'Cricket • Cup • Tournament',
        'format': 'ODI',
    },
    {
        'slug': 'legendary-eleven',
        'title': 'Legendary Eleven',
        'image': 'game25.jpg',
        'tagline': 'Build your dream side and relive classic cricket moments.',
        'description': 'Cricket • Legends • Strategy',
        'format': 'Test',
    },
    {
        'slug': 'cricket-rivals',
        'title': 'Cricket Rivals',
        'image': 'game16.jpg',
        'tagline': 'Challenge players worldwide and climb the global rankings.',
        'description': 'Cricket • Online • Multiplayer',
        'format': 'T20',
    },
    {
        'slug': 'ipl-masters',
        'title': 'IPL Masters',
        'image': 'game17.jpg',
        'tagline': 'Lead your favourite IPL team to championship glory.',
        'description': 'Cricket • IPL • Sports',
        'format': 'T20',
    },
    {
        'slug': 'cricket-battle',
        'title': 'Cricket Battle',
        'image': 'game18.jpg',
        'tagline': 'Play intense cricket matches with realistic gameplay.',
        'description': 'Cricket • Action • 3D',
        'format': 'ODI',
    },
    {
        'slug': 'super-sixes',
        'title': 'Super Sixes',
        'image': 'game19.jpg',
        'tagline': 'Smash massive sixes and complete exciting challenges.',
        'description': 'Cricket • Arcade • Fun',
        'format': 'T20',
    },
    {
        'slug': 'world-cup',
        'title': 'World Cup Cricket',
        'image': 'game20.jpg',
        'tagline': 'Compete against top nations and lift the World Cup trophy.',
        'description': 'Cricket • Tournament • Championship',
        'format': 'ODI',
        'embed_url': 'https://www.crazygames.com/embed/cricket-world-cup',
        'embed_provider': 'CrazyGames',
    },
    {
        'slug': 'cricket-rush',
        'title': 'Cricket Rush',
        'image': 'game26.jpg',
        'tagline': 'Experience rapid-fire cricket action with nonstop excitement.',
        'description': 'Cricket • Rush • Fast Play',
        'format': 'T20',
    },
    {
        'slug': 'captains-choice',
        'title': "Captain's Choice",
        'image': 'game27.jpg',
        'tagline': 'Lead your team with smart tactics and match-winning decisions.',
        'description': 'Cricket • Tactics • Manager',
        'format': 'Test',
    },
    {
        'slug': 'boundary-bash',
        'title': 'Boundary Bash',
        'image': 'game28.jpg',
        'tagline': 'Chase huge totals with explosive batting and stylish shots.',
        'description': 'Cricket • Big Hits • Arcade',
        'format': 'T20',
    },
    {
        'slug': 'spin-wizard',
        'title': 'Spin Wizard',
        'image': 'game29.jpg',
        'tagline': 'Outfox batsmen with clever spin and perfect line and length.',
        'description': 'Cricket • Spin • Precision',
        'format': 'Test',
    },
    {
        'slug': 't20-fever',
        'title': 'T20 Fever',
        'image': 'game30.jpg',
        'tagline': 'Enjoy high-energy T20 cricket packed with big moments.',
        'description': 'Cricket • T20 • Thrill',
        'format': 'T20',
    },
]


def resolve_game_slug(slug):
    if any(g['slug'] == slug for g in GAMES):
        return slug
    s = (slug or '').lower()
    keywords = {
        'world-cup': 'world-cup',
        'super-over': 'super-over',
        'champion': 'champion-cup',
        'ipl': 'ipl-2026',
        'street': 'street-cricket',
        'league': 'cricket-league-3d',
        'masters': 'ipl-masters',
        'rivals': 'cricket-rivals',
        'sixes': 'super-sixes',
        'bowling': 'fast-bowling',
        'stadium': 'stadium-clash',
        'bash': 'boundary-bash',
        'spin': 'spin-wizard',
        'rush': 'cricket-rush',
        'battle': 'cricket-battle',
        'power': 'power-hit',
        'legend': 'legendary-eleven',
        'test': 'fast-bowling',
        't20': 't20-fever',
        'cup': 'champion-cup',
        'trophy': 'champion-cup',
    }
    for key, target in sorted(keywords.items(), key=lambda kv: -len(kv[0])):
        if key in s:
            return target
    return None


def cricket_api(request, slug=None):
    if slug:
        game = next((g for g in GAMES if g['slug'] == slug), None)
        if not game:
            return JsonResponse({'error': 'Game not found'}, status=404)
        return JsonResponse({
            'game': game,
            'remaining_games': [g for g in GAMES if g['slug'] != slug],
            'total_games': len(GAMES),
        })
    return JsonResponse({'games': GAMES, 'total_games': len(GAMES)})


def game(request, slug):
    resolved = resolve_game_slug(slug)
    selected = next((g for g in GAMES if g['slug'] == resolved), GAMES[0])
    remaining = [g for g in GAMES if g['slug'] != selected['slug']]
    return render(request, 'application2/game.html', {
        'game': selected,
        'remaining_games': remaining,
        'remaining_json': json.dumps([{
            'slug': g['slug'],
            'title': g['title'],
            'image': g['image'],
            'tagline': g['tagline'],
            'description': g['description'],
        } for g in remaining]),
    })


def play_hub(request):
    if not request.user.is_authenticated:
        return redirect('registration')
    return render(request, 'application2/play.html', {
        'games': GAMES,
        'total_games': len(GAMES),
        'autostart': request.GET.get('autostart') == '1',
    })


def api_play_now(request):
    played = list(request.session.get('unique_played_slugs', []))
    seen = set(played)
    pool = [g for g in GAMES if g['slug'] not in seen]
    cycle_reset = False
    if not pool:
        played = []
        pool = list(GAMES)
        cycle_reset = True

    game = random.choice(pool)
    played.append(game['slug'])
    request.session['unique_played_slugs'] = played
    request.session.modified = True

    return JsonResponse({
        'game': game,
        'cycle_reset': cycle_reset,
        'unique_played_count': len(set(played)),
        'total_games': len(GAMES),
        'remaining_unique': len([g for g in GAMES if g['slug'] not in set(played)]),
        'next_url': reverse('game', args=[game['slug']]),
    })


def registration(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST

        mobile = data.get('mobile', '').strip()
        if not mobile:
            return JsonResponse({'error': 'Mobile number is required'}, status=400)

        user = User.objects.filter(username=mobile).first()
        if not user:
            user = User.objects.create_user(username=mobile, password=mobile)
            Profile.objects.create(user=user, mobile=mobile, full_name='Guest Player')

        login(request, user)
        return JsonResponse({'success': True, 'user_id': user.id})

    return render(request, 'application2/Registration.html')


def profile(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            profile_obj = Profile.objects.filter(user=request.user).last()
            if not profile_obj:
                profile_obj = Profile(user=request.user)
        else:
            profile_obj = Profile(user=None)
        full_name = request.POST.get('full_name', '').strip()
        if full_name:
            profile_obj.full_name = full_name
        email = request.POST.get('email', '').strip()
        if email:
            profile_obj.email = email
        mobile = request.POST.get('mobile', '').strip()
        if mobile:
            profile_obj.mobile = mobile
        dob_value = request.POST.get('date_of_birth', '').strip()
        if dob_value:
            try:
                profile_obj.date_of_birth = date.fromisoformat(dob_value)
            except ValueError:
                pass
        gender = request.POST.get('gender', '').strip()
        if gender:
            profile_obj.gender = gender
        location = request.POST.get('location', '').strip()
        if location:
            profile_obj.location = location
        about = request.POST.get('about', '').strip()
        if about:
            profile_obj.about = about
        avatar_data = request.POST.get('avatar_data', '').strip()
        if avatar_data:
            profile_obj.avatar_data = avatar_data
        profile_obj.save()
        return redirect(f"{reverse('profile')}?saved=1")

    profile_obj = None
    current_subscription = None
    if request.user.is_authenticated:
        profile_obj = Profile.objects.filter(user=request.user).order_by('-id').first()
        current_subscription = Subscription.objects.filter(user=request.user).order_by('-id').first()

    return render(request, 'application2/profile.html', {
        'current_profile': profile_obj,
        'current_subscription': current_subscription,
    })


def logout_view(request):
    logout(request)
    return redirect('registration')
