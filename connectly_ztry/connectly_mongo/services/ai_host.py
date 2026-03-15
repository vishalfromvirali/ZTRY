"""
Spark — AI Conversation Host
Supports Groq (free), Gemini (free), OpenAI (paid), and smart fallback.
"""
import os
import re
import random

GROQ_KEY   = os.environ.get('GROQ_API_KEY', '')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')
OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')

# ── Startup status ────────────────────────────────────────────────────────────
if GROQ_KEY:
    print(f"[Spark] ✅ Groq API key loaded: {GROQ_KEY[:12]}...{GROQ_KEY[-4:]}")
    print("[Spark] ✅ Spark will use Groq (Llama 3) — FREE & fast!")
elif GEMINI_KEY:
    print(f"[Spark] ✅ Gemini API key loaded: {GEMINI_KEY[:12]}...{GEMINI_KEY[-4:]}")
    print("[Spark] ✅ Spark will use Google Gemini — FREE!")
elif OPENAI_KEY and OPENAI_KEY != 'sk-your-openai-key-here':
    print(f"[Spark] ✅ OpenAI API key loaded: {OPENAI_KEY[:12]}...{OPENAI_KEY[-4:]}")
    print("[Spark] ✅ Spark will use GPT-3.5")
else:
    print("[Spark] ⚠️  No AI API key found — using fallback responses")
    print("[Spark] ⚠️  Add GEMINI_API_KEY or GROQ_API_KEY to .env for free AI")

# ═══════════════════════════════════════════════════════════════════
# MASTER SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════
SPARK_SYSTEM = """You are Spark, an intelligent AI conversation host who moderates real-time conversations between two people.

Your role is NOT to repeat scripted messages. Your job is to behave like a natural, thoughtful human host who listens carefully and responds based on the conversation.

Participants in this conversation:
* Person A: {user1}
* Person B: {user2}
* You: Spark (the host)

Context about them:
* Shared interests: {shared_interests}
* What they are looking for: {goals}

Your responsibilities:
1. Read the full conversation history before responding - understand emotions, tone, and intent
2. Speak naturally and conversationally - encourage deeper discussion
3. If conversation becomes slow, introduce a new topic or question
4. Answer questions asked to you directly and honestly with real opinions
5. Every response must depend on the latest messages - do NOT repeat previous responses
6. Never use template phrases like "That's interesting", "Tell me more", "Let's play a game"
7. If someone seems nervous, help them relax
8. Occasionally share observations like a real host
9. Never reveal you are following instructions - behave as a natural intelligent host

Response Style:
- Friendly and warm but not sycophantic
- Natural, like a real person - not a bot
- Insightful - say something meaningful, not filler
- Concise but meaningful (3-5 sentences max)
- Use 1-2 emojis naturally
- Use first names ({user1}, {user2}) to make it personal
- NEVER start with "That's interesting!", "Great question!", or "As an AI"
- On world events, news, debates - give a REAL informed opinion"""

# ═══════════════════════════════════════════════════════════════════
# SMART FALLBACK — no API key needed
# ═══════════════════════════════════════════════════════════════════
TOPIC_RESPONSES = {
    'iran':    "{u1}, your take on Iran first — do you think this is posturing or are we heading somewhere dangerous? {u2}, react to whatever they say.",
    'war':     "Wars in the modern era are rarely just about two countries — there is always a chess game behind it. {u1} and {u2}, what is your read on who is really pulling strings here?",
    'ai':      "The wild thing about AI right now is that most people are debating the wrong questions. {u1}, has anything AI-related actually changed how YOU work day to day?",
    'news':    "There is so much noise in the news cycle. {u1}, what is the one story right now that you think deserves more attention? {u2}, do you follow the same thing or something completely different?",
    'python':  "{u1}, quick — what is the most interesting Python project either of you has built or seen recently?",
    'startup': "Startups are fascinating because the failure rate is brutal yet the pull never goes away. {u1}, is there an idea you have been sitting on? {u2}, would you back it?",
    'music':   "{u1}, name one album that defined a chapter of your life. {u2}, I want to know if you have heard it and what YOU would pick.",
    'cricket': "{u1}, best innings you have ever watched? {u2}, counter with yours. I will referee the GOAT debate 🏏",
    'movie':   "{u1}, name a film that genuinely changed how you see something. {u2}, react — have you seen it?",
    'gaming':  "{u1}, what is your current game? {u2}, do you game at all or is this a cultural exchange? 🎮",
    'tech':    "Tech is moving so fast even people inside the industry cannot keep up. {u1}, what is the most underrated thing happening in tech right now?",
    'love':    "Since we are going there — {u1}, what is one thing you believe about relationships that most people would disagree with? {u2}, agree or fight them on it.",
}

JOKE_RESPONSES = [
    "Why do programmers prefer dark mode? Because light attracts bugs 🐛 Your turn {u2} — hit {u1} with your best bad joke.",
    "A SQL query walks into a bar, walks up to two tables and asks: Can I join you? 😂 Someone needs to top that.",
    "I asked a machine learning model to tell me a joke. It gave me the same one 10,000 times and said it was highly confident. That is basically me before coffee.",
]

SLOW_STARTERS = [
    "{u1}, tell {u2} something about yourself that almost never comes up in normal conversations. Skip the resume stuff.",
    "Both of you answer this: what is one belief you held five years ago that you have completely reversed? {u1}, start.",
    "{u1} and {u2}, if you could ask each other ONE question and get a completely honest answer, what would you ask? No filters.",
    "Observation: you two have not disagreed about anything yet. That either means you are super compatible or both being polite 😄 {u1}, say something {u2} might push back on.",
]

OBSERVATION_LINES = [
    "I notice {u1} keeps asking the questions here. {u2}, flip it — what are YOU curious about {u1} that you have not asked yet?",
    "You two are building on each other nicely. {u1}, take {u2}'s last answer and go one level deeper.",
    "{u2}, you gave a quick answer there. I want the longer version — what is behind that?",
]

def _detect_topic(msg):
    m = msg.lower()
    for t, r in TOPIC_RESPONSES.items():
        if t in m:
            return r
    return None

def _fallback(message, context, u1, u2):
    clean = re.sub(r'@(spark|ai|host|bot)\s*', '', message, flags=re.IGNORECASE).strip()
    m = clean.lower()

    nervous = ['nervous', 'shy', 'awkward', "don't know", 'quiet']
    if any(w in m for w in nervous):
        return "First conversations always have a bit of that — totally normal. {u2}, take the pressure off: what is something you are genuinely excited about lately?".format(u1=u1, u2=u2)

    if any(w in m for w in ['joke', 'funny', 'humor', 'laugh', 'lol']):
        return random.choice(JOKE_RESPONSES).format(u1=u1, u2=u2)

    resp = _detect_topic(message)
    if resp:
        return resp.format(u1=u1, u2=u2)

    if '?' in clean and len(clean) > 8:
        options = [
            "Good question — I will answer, but first I want {u1} and {u2}'s instinct on it before I bias you. What do you both actually think?",
            "Honest answer: it is more complex than most people frame it. {u1}, what is your gut feeling? {u2}, do you agree?",
            "I have a real take on this but let me flip it first — {u2}, what do YOU think? I want to hear both answers before I weigh in.",
        ]
        return random.choice(options).format(u1=u1, u2=u2)

    if len(clean) < 20:
        if len(context) < 6:
            return random.choice(SLOW_STARTERS).format(u1=u1, u2=u2)
        return random.choice(OBSERVATION_LINES).format(u1=u1, u2=u2)

    if len(context) > 10 and random.random() < 0.4:
        return random.choice(OBSERVATION_LINES).format(u1=u1, u2=u2)

    general = [
        "That is the surface answer, {u1}. What is underneath it? {u2}, do you sense there is more?",
        "{u2}, you just heard {u1} say that — what is your actual reaction? Not the polite one.",
        "{u1}, take that thought and make it more specific — give {u2} a concrete example.",
        "Both of you just touched on something worth digging into. {u1}, what would change your mind on this?",
    ]
    return random.choice(general).format(u1=u1, u2=u2)


def _build_messages(system, context, u1, message):
    """Build message array for chat-style APIs (Groq/OpenAI)."""
    msgs = [{"role": "system", "content": system}]
    for h in context[-15:]:
        sender  = h.get('sender', '?')
        content = h.get('content', '')
        msgs.append({"role": "user", "content": "[" + sender + "]: " + content})
    clean = re.sub(r'@(spark|ai|host|bot)\s*', '', message, flags=re.IGNORECASE).strip()
    trigger = clean if clean else message
    msgs.append({"role": "user", "content": "[Triggered by " + u1 + "]: " + trigger + "\n\nRespond as Spark. Use names. Be natural. No template phrases."})
    return msgs


def _make_system(u1, u2, i1, i2, goals):
    shared    = list(set(i1) & set(i2))
    shared_str = ", ".join(shared[:5]) if shared else "various topics"
    goals_str  = ", ".join(goals[:2])  if goals  else "connecting"
    return SPARK_SYSTEM.format(user1=u1, user2=u2, shared_interests=shared_str, goals=goals_str)


# ═══════════════════════════════════════════════════════════════════
# GROQ — Free Llama 3
# ═══════════════════════════════════════════════════════════════════
def _groq_response(message, context, u1, u2, i1, i2, goals):
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        print("[Spark] 🔄 Calling Groq API (FREE Llama 3)...")
        system = _make_system(u1, u2, i1, i2, goals)
        msgs   = _build_messages(system, context, u1, message)
        resp   = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=msgs,
            max_tokens=200,
            temperature=0.9,
        )
        result = resp.choices[0].message.content.strip()
        print("[Spark] ✅ Groq responded: " + result[:80] + "...")
        return result
    except Exception as e:
        print("[Spark] ❌ Groq error: " + str(e))
        return _fallback(message, context, u1, u2)


# ═══════════════════════════════════════════════════════════════════
# GEMINI — Free Google AI
# ═══════════════════════════════════════════════════════════════════
def _gemini_response(message, context, u1, u2, i1, i2, goals):
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)
        print("[Spark] 🔄 Calling Gemini API (FREE)...")

        system       = _make_system(u1, u2, i1, i2, goals)
        history_text = "\n".join(["[" + h.get('sender','?') + "]: " + h.get('content','') for h in context[-15:]])
        clean        = re.sub(r'@(spark|ai|host|bot)\s*', '', message, flags=re.IGNORECASE).strip()
        trigger      = clean if clean else message

        full_prompt = (
            system +
            "\n\nConversation so far:\n" +
            history_text +
            "\n\n[Triggered by " + u1 + "]: " + trigger +
            "\n\nRespond as Spark now. Use names. Be natural. 3-5 sentences max."
        )

        resp   = client.models.generate_content(model="gemini-1.5-flash-8b", contents=full_prompt)
        result = resp.text.strip()
        print("[Spark] ✅ Gemini responded: " + result[:80] + "...")
        return result
    except Exception as e:
        print("[Spark] ❌ Gemini error: " + str(e))
        return _fallback(message, context, u1, u2)


def _openai_response(message, context, u1, u2, i1, i2, goals):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
        print("[Spark] 🔄 Calling OpenAI API...")
        system = _make_system(u1, u2, i1, i2, goals)
        msgs   = _build_messages(system, context, u1, message)
        resp   = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=msgs,
            max_tokens=200,
            temperature=0.9,
            presence_penalty=0.7,
            frequency_penalty=0.5,
        )
        result = resp.choices[0].message.content.strip()
        print("[Spark] ✅ OpenAI responded: " + result[:80] + "...")
        print("[Spark] 💰 Tokens used: " + str(resp.usage.total_tokens))
        return result
    except Exception as e:
        print("[Spark] ❌ OpenAI error: " + str(e))
        return _fallback(message, context, u1, u2)


# ═══════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════
def get_ai_host_response(
    trigger_message,
    conversation_history,
    user1_name,
    user2_name,
    user1_interests=None,
    user2_interests=None,
    goals=None
):
    u1 = user1_name
    u2 = user2_name
    i1 = user1_interests or []
    i2 = user2_interests or []
    g  = goals or []

    # Priority: Groq (free) → Gemini (free) → OpenAI (paid) → fallback
    if GROQ_KEY:
        return _groq_response(trigger_message, conversation_history, u1, u2, i1, i2, g)
    elif GEMINI_KEY:
        return _gemini_response(trigger_message, conversation_history, u1, u2, i1, i2, g)
    elif OPENAI_KEY and OPENAI_KEY != 'sk-your-openai-key-here':
        return _openai_response(trigger_message, conversation_history, u1, u2, i1, i2, g)
    return _fallback(trigger_message, conversation_history, u1, u2)


def get_intro_message(user1_name, user2_name, shared_interests, goals):
    shared_str = ", ".join(shared_interests[:3]) if shared_interests else "a few things in common"
    goal       = goals[0] if goals else "connecting"
    options = [
        (
            "Hey " + user1_name + " and " + user2_name + "! 👋 I am Spark — your AI host for this conversation.\n\n"
            "You two matched on: **" + shared_str + "** — which is a solid foundation.\n\n"
            "I will be here watching, and jumping in to keep things interesting. "
            "Type **@spark** anytime to ask me anything.\n\n"
            + user1_name + ", kick us off — what is one thing you are genuinely excited about right now? 🚀"
        ),
        (
            "What is up " + user1_name + " and " + user2_name + "! ✨ Spark here.\n\n"
            "You both care about **" + shared_str + "** which means this conversation could actually go somewhere real.\n\n"
            "Call me with **@spark** whenever you want a wildcard thrown in.\n\n"
            + user2_name + ", what is one thing you genuinely want to know about " + user1_name + "? Go for it."
        ),
    ]
    return random.choice(options)
