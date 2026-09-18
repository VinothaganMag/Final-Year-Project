import re
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from urllib.parse import urlparse


# ═══════════════════════════════════════════════
# SUSPICIOUS KEYWORDS
# ═══════════════════════════════════════════════

SUSPICIOUS_KEYWORDS = [
    'login', 'verify', 'bank', 'free', 'secure', 'update',
    'confirm', 'account', 'password', 'signin', 'submit',
    'suspend', 'restrict', 'urgent', 'click', 'winner',
    'prize', 'offer', 'limited', 'expire'
]


# ═══════════════════════════════════════════════
# URL FEATURE EXTRACTION
# ═══════════════════════════════════════════════

FEATURE_NAMES = [
    'URL Length', 'Number of Dots', 'Number of Digits',
    'Special Characters', 'HTTPS Present', 'Contains IP Address',
    'Suspicious Keywords', 'Subdomains', 'Has @ Symbol',
    'Hyphens Count', 'Path Length', 'Has Redirect', 'URL Parameters'
]


def extract_url_features(url: str) -> dict:
    url_lower = url.lower().strip()
    if not url_lower.startswith(('http://', 'https://')):
        parse_url = 'http://' + url_lower
    else:
        parse_url = url_lower

    parsed = urlparse(parse_url)

    url_length = len(url_lower)
    num_dots = url_lower.count('.')
    num_digits = sum(c.isdigit() for c in url_lower)
    num_special = sum(not c.isalnum() and c not in './:' for c in url_lower)
    has_https = 1 if url_lower.startswith('https://') else 0

    ip_pattern = re.compile(
        r'(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)'
    )
    has_ip = 1 if ip_pattern.search(url_lower) else 0

    found_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in url_lower]
    num_suspicious = len(found_keywords)
    num_subdomains = len(parsed.hostname.split('.')) - 1 if parsed.hostname else 0
    has_at = 1 if '@' in url_lower else 0
    num_hyphens = url_lower.count('-')
    path_length = len(parsed.path)
    has_redirect = 1 if '//' in parsed.path else 0
    num_params = len(parsed.query.split('&')) if parsed.query else 0

    return {
        'url_length': url_length,
        'num_dots': num_dots,
        'num_digits': num_digits,
        'num_special_chars': num_special,
        'has_https': has_https,
        'has_ip_address': has_ip,
        'num_suspicious_keywords': num_suspicious,
        'found_keywords': found_keywords,
        'num_subdomains': num_subdomains,
        'has_at_symbol': has_at,
        'num_hyphens': num_hyphens,
        'path_length': path_length,
        'has_redirect': has_redirect,
        'num_params': num_params,
    }


def url_features_to_array(features: dict) -> np.ndarray:
    return np.array([[
        features['url_length'], features['num_dots'], features['num_digits'],
        features['num_special_chars'], features['has_https'], features['has_ip_address'],
        features['num_suspicious_keywords'], features['num_subdomains'],
        features['has_at_symbol'], features['num_hyphens'], features['path_length'],
        features['has_redirect'], features['num_params'],
    ]])


def calculate_risk_score(features: dict) -> tuple:
    score = 0
    reasons = []

    if features['url_length'] > 75:
        score += 20
        reasons.append(f"URL is unusually long ({features['url_length']} chars)")
    elif features['url_length'] > 50:
        score += 10
        reasons.append(f"URL is moderately long ({features['url_length']} chars)")

    kw = features['found_keywords']
    if len(kw) >= 3:
        score += 30
        reasons.append(f"Multiple suspicious keywords: {', '.join(kw)}")
    elif len(kw) >= 1:
        score += 15 + len(kw) * 5
        reasons.append(f"Suspicious keyword(s): {', '.join(kw)}")

    if features['has_https'] == 0:
        score += 20
        reasons.append("No HTTPS — insecure connection")

    if features['num_dots'] > 4:
        score += 10
        reasons.append(f"Excessive dots ({features['num_dots']}), possible subdomain abuse")
    elif features['num_dots'] > 3:
        score += 5
        reasons.append(f"Above-average dots ({features['num_dots']})")

    if features['has_ip_address']:
        score += 15
        reasons.append("URL contains IP address instead of domain")

    if features['num_special_chars'] > 5:
        score += 10
        reasons.append(f"High special character count ({features['num_special_chars']})")

    if features['has_at_symbol']:
        score += 10
        reasons.append("Contains @ symbol — possible obfuscation")

    if features['has_redirect']:
        score += 10
        reasons.append("Has redirect pattern (//) in path")

    if features['num_digits'] > 6:
        score += 5
        reasons.append(f"Many digits in URL ({features['num_digits']})")

    if features['num_params'] > 3:
        score += 5
        reasons.append(f"Many query parameters ({features['num_params']})")

    score = min(score, 100)
    if score == 0:
        reasons.append("No suspicious indicators detected")

    return score, reasons


def classify_risk(score: int) -> str:
    if score <= 30:
        return 'Safe'
    elif score <= 60:
        return 'Suspicious'
    return 'Dangerous'


# ═══════════════════════════════════════════════
# BUILD URL MODEL (RandomForest)
# ═══════════════════════════════════════════════

def build_url_model():
    np.random.seed(42)
    n = 600

    safe = np.column_stack([
        np.random.randint(10, 40, n),
        np.random.randint(1, 3, n),
        np.random.randint(0, 3, n),
        np.random.randint(0, 2, n),
        np.ones(n),
        np.zeros(n),
        np.zeros(n),
        np.random.randint(1, 3, n),
        np.zeros(n),
        np.random.randint(0, 2, n),
        np.random.randint(1, 15, n),
        np.zeros(n),
        np.random.randint(0, 2, n),
    ])

    phish = np.column_stack([
        np.random.randint(50, 120, n),
        np.random.randint(3, 8, n),
        np.random.randint(3, 15, n),
        np.random.randint(3, 10, n),
        np.random.choice([0, 1], n, p=[0.7, 0.3]),
        np.random.choice([0, 1], n, p=[0.6, 0.4]),
        np.random.randint(1, 5, n),
        np.random.randint(3, 7, n),
        np.random.choice([0, 1], n, p=[0.7, 0.3]),
        np.random.randint(2, 6, n),
        np.random.randint(15, 60, n),
        np.random.choice([0, 1], n, p=[0.5, 0.5]),
        np.random.randint(2, 8, n),
    ])

    X = np.vstack([safe, phish])
    y = np.array([0] * n + [1] * n)

    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X, y)
    return model


# ═══════════════════════════════════════════════
# BUILD MAIL MODEL (TF-IDF + LogisticRegression)
# ═══════════════════════════════════════════════

SPAM_SAMPLES = [
    "Congratulations! You have won a free iPhone. Click here to claim your prize now!",
    "URGENT: Your bank account has been compromised. Verify your identity immediately.",
    "You are the lucky winner of $1,000,000! Click the link to claim.",
    "Free gift card! Limited time offer. Act now before it expires.",
    "Your account will be suspended unless you update your password immediately.",
    "Dear customer, your payment of $500 is pending. Confirm now to avoid cancellation.",
    "Click here to verify your PayPal account. Failure to respond will result in suspension.",
    "You have been selected for an exclusive offer! Get 90% off luxury watches.",
    "WARNING: Unusual login detected on your account. Reset password immediately.",
    "Earn $5000 per week working from home! No experience needed. Sign up today.",
    "Your Amazon order has been shipped. Click to track. Verify your card details.",
    "FINAL WARNING: Your Netflix subscription expires today. Update billing now.",
    "Free trial of premium software. Download now. No credit card required.",
    "You've received a secure document. Login to view. Verify identity first.",
    "Urgent wire transfer request from CEO. Process immediately. Confidential.",
    "Congratulations winner! You've been randomly selected. Claim prize money now!",
    "Your Apple ID has been locked. Restore access by verifying your information.",
    "Make money fast! Guaranteed returns. Invest now. Limited seats available.",
    "Security alert: unauthorized access attempt. Click link to secure account.",
    "You qualify for a government grant of $10,000. Apply now before deadline.",
    "Hot singles in your area want to meet you! Click to join free dating site.",
    "Your package could not be delivered. Click to reschedule and pay shipping fee.",
    "Exclusive crypto investment opportunity. 500% returns guaranteed. Act fast!",
    "IRS notification: You owe back taxes. Pay immediately to avoid legal action.",
    "Cheap medications online! No prescription needed. Free shipping worldwide.",
    "Your social security number has been compromised. Call immediately to verify.",
    "Win a brand new car! Enter our sweepstakes now. No purchase necessary.",
    "Bank of America security update. Confirm your account details immediately.",
    "Get rich quick with this one simple trick! Financial freedom guaranteed.",
    "Your WhatsApp account will expire. Verify now to keep your messages.",
]

HAM_SAMPLES = [
    "Hi team, the meeting is rescheduled to 3 PM tomorrow. Please update your calendars.",
    "Can you send me the quarterly report by end of day? Thanks.",
    "Reminder: Project deadline is next Friday. Let's sync up this week.",
    "I'll be working from home today. Reach me on Slack if needed.",
    "Here are the meeting notes from yesterday's standup. Please review.",
    "The new feature has been deployed to staging. Please test when you can.",
    "Happy birthday! Hope you have a wonderful day with family and friends.",
    "Lunch meeting at noon in conference room B. Bring your laptops.",
    "Please find attached the invoice for last month's services.",
    "The server maintenance is scheduled for this Saturday at 2 AM.",
    "Great job on the presentation today. The client was impressed.",
    "Could you review my pull request when you get a chance? No rush.",
    "Family dinner this Sunday at 6 PM. Let me know if you can make it.",
    "The new office supplies have arrived. Pick them up from reception.",
    "Attached is the updated project timeline. Let me know your thoughts.",
    "Thanks for helping with the bug fix yesterday. Really appreciate it.",
    "Team outing planned for next month. Please fill out the survey.",
    "Your order has been confirmed and will be delivered in 3-5 business days.",
    "Welcome to the team! Your onboarding starts Monday at 9 AM.",
    "The quarterly review meeting is set for next Wednesday at 10 AM.",
    "Can we schedule a call to discuss the new requirements?",
    "I've shared the document with you on Google Drive. Please check.",
    "Thanks for the feedback on the design mockups. I'll make the revisions.",
    "The parking lot will be closed for maintenance this weekend.",
    "Please submit your timesheets by end of day Friday.",
    "Looking forward to the conference next week. See you there!",
    "The wifi password for the guest network has been changed. Check Slack.",
    "I've updated the dependencies in the project. Please pull latest.",
    "Dinner reservation for 4 at 7 PM tonight. Restaurant is downtown.",
    "Your dentist appointment is confirmed for Thursday at 2 PM.",
]


def build_mail_model():
    texts = SPAM_SAMPLES + HAM_SAMPLES
    labels = [1] * len(SPAM_SAMPLES) + [0] * len(HAM_SAMPLES)

    vectorizer = TfidfVectorizer(max_features=3000, stop_words='english', ngram_range=(1, 2))
    X = vectorizer.fit_transform(texts)

    model = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
    model.fit(X, labels)

    return vectorizer, model


# ═══════════════════════════════════════════════
# INITIALIZE MODELS AT IMPORT
# ═══════════════════════════════════════════════

print("[*] Training URL model (RandomForest)...")
url_model = build_url_model()
print("[OK] URL model ready")

print("[*] Training Mail model (TF-IDF + LogisticRegression)...")
mail_vectorizer, mail_model = build_mail_model()
print("[OK] Mail model ready")


# ═══════════════════════════════════════════════
# PREDICTION FUNCTIONS
# ═══════════════════════════════════════════════

def predict_url(url: str) -> dict:
    features = extract_url_features(url)
    X = url_features_to_array(features)

    ml_pred = url_model.predict(X)[0]
    ml_proba = url_model.predict_proba(X)[0]

    risk_score, reasons = calculate_risk_score(features)
    phishing_conf = ml_proba[1] * 100
    blended = int(0.6 * risk_score + 0.4 * phishing_conf)
    blended = min(blended, 100)

    status = classify_risk(blended)
    importances = url_model.feature_importances_

    feature_keys = [
        'url_length', 'num_dots', 'num_digits', 'num_special_chars',
        'has_https', 'has_ip_address', 'num_suspicious_keywords',
        'num_subdomains', 'has_at_symbol', 'num_hyphens',
        'path_length', 'has_redirect', 'num_params',
    ]

    breakdown = []
    for i, key in enumerate(feature_keys):
        breakdown.append({
            'name': FEATURE_NAMES[i],
            'value': int(features[key]),
            'importance': round(importances[i] * 100, 1),
        })

    return {
        'risk_score': blended,
        'status': status,
        'reasons': reasons,
        'features': breakdown,
        'ml_prediction': 'Phishing' if ml_pred == 1 else 'Legitimate',
        'ml_confidence': round(max(ml_proba) * 100, 1),
        'phishing_probability': round(phishing_conf, 1),
    }


def predict_mail(message: str) -> dict:
    X = mail_vectorizer.transform([message])
    pred = mail_model.predict(X)[0]
    proba = mail_model.predict_proba(X)[0]

    label = 'Spam / Phishing' if pred == 1 else 'Legitimate'
    confidence = round(max(proba) * 100, 1)
    spam_prob = round(proba[1] * 100, 1)

    # Find suspicious words in the message
    words = re.findall(r'\b\w+\b', message.lower())
    alert_words = [
        'free', 'winner', 'click', 'urgent', 'verify', 'account', 'password',
        'claim', 'prize', 'offer', 'limited', 'expire', 'suspend', 'bank',
        'login', 'confirm', 'immediately', 'update', 'secure', 'selected',
        'congratulations', 'guaranteed', 'warning', 'unauthorized', 'locked',
        'compromised', 'wire', 'transfer'
    ]
    found_alert = list(set(w for w in words if w in alert_words))

    reasons = []
    if found_alert:
        reasons.append(f"Contains suspicious words: {', '.join(found_alert[:8])}")
    if pred == 1:
        reasons.append("Message pattern matches known spam/phishing templates")
        if spam_prob > 80:
            reasons.append("Very high spam probability detected")
    else:
        reasons.append("Message appears to be normal communication")
    if '!' in message and message.count('!') > 2:
        reasons.append("Excessive use of exclamation marks")
    if any(w in message.lower() for w in ['click here', 'act now', 'limited time']):
        reasons.append("Contains urgency cues commonly used in phishing")

    return {
        'prediction': label,
        'confidence': confidence,
        'spam_probability': spam_prob,
        'suspicious_words': found_alert,
        'reasons': reasons,
        'is_spam': bool(pred == 1),
    }
