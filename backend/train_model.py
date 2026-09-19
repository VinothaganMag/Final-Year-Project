"""
train_model.py
==============
Ensemble Model Based Phishing Detection
Using Hybrid Features: TF-IDF + Structural URL Features

Run from the backend/ directory:
    python train_model.py
"""

import os
import re

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.svm import SVC

# ─────────────────────────────────────────────
# DATASET  (200 balanced samples)
# ─────────────────────────────────────────────
SAFE_URLS = [
    "https://www.google.com",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://github.com/torvalds/linux",
    "https://stackoverflow.com/questions/tagged/python",
    "https://www.amazon.com/dp/B09XXXXXX",
    "https://www.wikipedia.org/wiki/Machine_learning",
    "https://www.reddit.com/r/programming",
    "https://twitter.com/elonmusk",
    "https://www.linkedin.com/in/sample-user",
    "https://www.microsoft.com/en-us/windows",
    "https://docs.python.org/3/library/os.html",
    "https://www.apple.com/iphone",
    "https://www.netflix.com/browse",
    "https://www.bbc.com/news/world",
    "https://www.nytimes.com/section/technology",
    "https://www.nasa.gov/topics/moon",
    "https://arxiv.org/abs/2109.00001",
    "https://www.kaggle.com/datasets",
    "https://huggingface.co/models",
    "https://www.coursera.org/learn/machine-learning",
    "https://en.wikipedia.org/wiki/Phishing",
    "https://www.cloudflare.com/learning/ddos",
    "https://www.forbes.com/technology",
    "https://techcrunch.com/startups",
    "https://www.medium.com/towards-data-science",
    "https://www.shopify.com/blog",
    "https://stripe.com/docs/payments",
    "https://developer.mozilla.org/en-US/docs/Web",
    "https://www.w3schools.com/python",
    "https://flask.palletsprojects.com/en/3.0.x",
    "https://scikit-learn.org/stable/modules/ensemble.html",
    "https://pandas.pydata.org/docs",
    "https://numpy.org/doc/stable",
    "https://matplotlib.org/stable/gallery",
    "https://www.twitch.tv/directory",
    "https://www.instagram.com/explore",
    "https://www.spotify.com/us/signup",
    "https://www.zoom.us/join",
    "https://slack.com/intl/en-us",
    "https://notion.so/templates",
    "https://www.figma.com/community",
    "https://vercel.com/dashboard",
    "https://www.heroku.com/free",
    "https://aws.amazon.com/ec2",
    "https://cloud.google.com/storage",
    "https://azure.microsoft.com/en-us/products",
    "https://www.digitalocean.com/products/droplets",
    "https://www.mongodb.com/cloud",
    "https://firebase.google.com/docs",
    "https://www.postgresql.org/docs",
    "https://www.mysql.com/products",
    "https://redis.io/docs",
    "https://www.elastic.co/elasticsearch",
    "https://kubernetes.io/docs",
    "https://www.docker.com/products/docker-desktop",
    "https://www.jenkins.io/doc",
    "https://grafana.com/grafana/dashboards",
    "https://prometheus.io/docs",
    "https://www.terraform.io/docs",
    "https://www.ansible.com/overview",
    "https://www.vagrantup.com/docs",
    "https://www.deviantart.com/popular",
    "https://unsplash.com/s/photos/nature",
    "https://www.pexels.com/videos",
    "https://pixabay.com/images/search/sky",
    "https://www.behance.net/galleries",
    "https://dribbble.com/shots",
    "https://www.canva.com/templates",
    "https://fonts.google.com/specimen/Inter",
    "https://icons8.com/icons",
    "https://fontawesome.com/icons",
    "https://www.w3.org/standards",
    "https://www.json.org/json-en.html",
    "https://openai.com/blog",
    "https://www.deepmind.com/research",
    "https://www.tensorflow.org/tutorials",
    "https://pytorch.org/tutorials",
    "https://keras.io/api",
    "https://xgboost.readthedocs.io",
    "https://lightgbm.readthedocs.io",
    "https://catboost.ai/docs",
    "https://www.statsmodels.org/stable",
    "https://scipy.org/doc/scipy",
    "https://www.sympy.org/en/index.html",
    "https://seaborn.pydata.org/examples",
    "https://plotly.com/python",
    "https://bokeh.org/gallery",
    "https://www.tableau.com/products",
    "https://powerbi.microsoft.com",
    "https://looker.com",
    "https://datastudio.google.com",
    "https://www.metabase.com",
    "https://superset.apache.org",
    "https://airflow.apache.org/docs",
    "https://dbt-labs.com/product/dbt-core",
    "https://www.fivetran.com/solutions",
    "https://segment.com/docs",
    "https://snowflake.com/en/data-cloud",
    "https://databricks.com/product/delta-lake",
]

PHISH_URLS = [
    "http://paypal.com-secure-login.ru/account/verify?token=abc123",
    "http://192.168.1.1/login/bank-verify.php",
    "http://amazon-free-gift.tk/claim?user=winner&ref=promo",
    "http://secure-update.paypal-login.ml/verify-account",
    "http://login.microsoftonline.com-secure.ml/auth/enter",
    "http://apple-id-locked.com/unlock?session=XYZ987",
    "http://free-bitcoin-2024.cf/get?amount=1BTC",
    "http://bankofamerica-secure.net/secure/login.php",
    "http://verify-your-account.tk/users/confirm",
    "http://ebay-suspended-notice.ru/reinstate/now",
    "http://172.16.0.1/phish/login.html",
    "http://google-prize-winner.gq/collect?code=WIN500",
    "http://netflix-billing-update.info/payment/retry",
    "http://support-apple-com.ml/iforgot/password",
    "http://chase-bank-alert.ru/secure/signin",
    "http://wellsfargo.online-login.cf/banking/secure",
    "http://irs-refund-portal.gq/claim/tax-refund",
    "http://10.0.0.1/admin/phish.php?redirect=bank",
    "http://facebook-security-alert.tk/checkpoint/verify",
    "http://instagram-verify-account.ml/confirm?id=12345",
    "http://whatsapp-free-prize.ru/unlock-gold-membership",
    "http://amazon-order-problem.gq/resolution/login",
    "http://dhl-delivery-failed.tk/reschedule?pkg=PKG001",
    "http://fedex-track-package-alert.ml/confirm",
    "http://usps-package-held.cf/delivery/confirm-address",
    "http://microsoft-account-security.ru/verify",
    "http://google-workspace-locked.tk/unlock/admin",
    "http://binance-wallet-verify.ml/2fa-reset",
    "http://coinbase-account-suspended.gq/reinstate",
    "http://metamask-recovery-phrase.ru/restore-wallet",
    "http://free-robux-generator.tk/claim?user=pro",
    "http://steam-free-csgo-knife.ml/redeem",
    "http://discord-nitro-free-month.cf/activate",
    "http://login.verify-secure.paypal-support.xyz/case",
    "http://account-suspended-amazon.site/verify?id=USR",
    "http://secure.banking.update-info.club/signin",
    "http://win-iphone15-apple.store/collect?code=APPLE",
    "http://bank-alert-secure.online/login?redirect=chase",
    "http://password-reset-google.pro/reset?token=xXxXx",
    "http://confirm-identity-facebook.buzz/review",
    "http://verify-paypal-identity.info/confirm?session=S1",
    "http://secure-bank-login.site/signin.php?bank=wells",
    "http://account-verify-ebay.live/confirm?uid=U99",
    "http://netflix-account-issue.online/update/payment",
    "http://irs-tax-return-portal.site/submit?ssn=XXXXXX",
    "http://free-amazon-voucher.club/redeem?code=AMZN500",
    "http://alert-banking-login.pro/secure?session=sess1",
    "http://apple-id-verify.info/apple-support/verify",
    "http://support-paypal-helpdesk.site/case?id=C00123",
    "http://microsoft-prize.online/collect?code=MS1000",
    "http://phish-site-login.net/banking/secure-login.php",
    "http://secure-account-bank-login.xyz/users/enter",
    "http://login-verify-account-check.ru/users/confirm",
    "http://free-gift-amazon-special.tk/redeem?ref=AFF",
    "http://bank-online-verify.ml/auth/signin",
    "http://paypal-security-alert.gq/unusual-activity",
    "http://confirm-your-email-bank.cf/email/verify",
    "http://wallet-backup-crypto.ru/restore?phrase=seed",
    "http://nft-free-mint-exclusive.tk/connect-wallet",
    "http://trust-wallet-verify.ml/import?phrase=seed",
    "http://uniswap-airdrop-claim.gq/connect?reward=ETH",
    "http://opensea-account-verify.cf/signin?redirect=nft",
    "http://crypto-wallet-drain.ru/connect",
    "http://seed-phrase-recovery.tk/restore?network=eth",
    "http://defi-yield-farm-bonus.ml/deposit?apy=9999",
    "http://flash-loan-attack.gq/exploit?profit=1eth",
    "http://blockchain-verify-kyc.cf/identity?id=KYC001",
    "http://fake-binance-launchpad.ru/register?ref=aff",
    "http://phishing-crypto-airdrop.tk/claim?token=drop",
    "http://web3-login-verify.ml/metamask?chain=eth",
    "http://pump-dump-token.gq/invest?coin=SCAM",
    "http://rugpull-defi.cf/stake?pool=honeypot",
    "http://drainer-nft-site.ru/mint?collection=FAKE",
    "http://free-eth-giveaway.tk/claim?wallet=0x000",
    "http://elon-sends-bitcoin.ml/double?amount=1btc",
    "http://bitforex-withdrawal-issue.gq/verify-account",
    "http://kraken-locked-account.cf/unlock?code=KRK",
    "http://okx-kyc-required.ru/verify?user=TRADER",
    "http://bybit-deposit-bonus.tk/claim?bonus=500usdt",
    "http://kucoin-referral-reward.ml/redeem?ref=KU999",
    "http://gate-io-security-alert.gq/2fa-reset?uid=USR",
    "http://huobi-account-blocked.cf/support?case=HB001",
    "http://mexc-free-listing.ru/invest?token=PUMP",
    "http://bkash-login-verify.tk/account?mobile=XXXXX",
    "http://bank-transfer-fake.ml/send?amount=99999",
    "http://sbi-netbanking-alert.gq/login?redirect=SBI",
    "http://hdfc-bank-secure.cf/netbanking/login",
    "http://icici-online-verify.ru/confirm?ref=ICICI",
    "http://axis-bank-reward.tk/redeem?points=50000",
    "http://kotak-mahindra-otp.ml/verify?otp=XXXXXX",
    "http://pnb-kyc-update.gq/upload?docs=aadhar",
    "http://union-bank-phish.cf/login?session=sess99",
    "http://canara-alert-login.ru/secure?id=CB0001",
    "http://bob-banking-verify.tk/account/confirm",
    "http://idbi-reward-claim.ml/redeem?code=IDBIWIN",
    "http://yes-bank-blocked.gq/reinstate?id=YBL001",
    "http://rbl-card-verify.cf/credit-card/otp",
    "http://indusind-login-phish.ru/netbanking/secure",
    "http://federal-kyc-required.tk/verify?id=FEDKY",
    "http://south-india-bank.ml/login?redirect=SIB",
    "http://karur-bank-alert.gq/confirm?session=KV001",
]

urls = SAFE_URLS + PHISH_URLS
labels = [0] * len(SAFE_URLS) + [1] * len(PHISH_URLS)

df = pd.DataFrame({"url": urls, "label": labels})
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

print(f"Dataset: {len(df)} samples  |  Safe={sum(df.label==0)}  Phishing={sum(df.label==1)}")


# ─────────────────────────────────────────────
# FEATURE ENGINEERING
# ─────────────────────────────────────────────
SUSPICIOUS_WORDS = [
    "login",
    "verify",
    "bank",
    "free",
    "secure",
    "update",
    "account",
    "confirm",
    "suspend",
    "unlock",
    "claim",
    "reward",
    "urgent",
    "alert",
    "password",
    "credential",
    "wallet",
    "crypto",
]

IP_PATTERN = re.compile(r"(\d{1,3}\.){3}\d{1,3}")


def extract_features(url: str) -> list:
    url_lower = url.lower()
    return [
        len(url),  # 1. URL length
        url.count("."),  # 2. number of dots
        url.count("-"),  # 3. number of hyphens
        url.count("_"),  # 4. number of underscores
        sum(c.isdigit() for c in url),  # 5. digit count
        1 if url_lower.startswith("https") else 0,  # 6. https present
        1 if IP_PATTERN.search(url) else 0,  # 7. contains IP address
        sum(1 for w in SUSPICIOUS_WORDS if w in url_lower),  # 8. suspicious word count
        url.count("/"),  # 9. slash count
        url.count("?"),  # 10. query string present
        url.count("="),  # 11. param count
        url.count("@"),  # 12. @ symbol (rare, phishing)
        len(url.split("//")[-1].split("/")[0]),  # 13. hostname length
        url.count("%"),  # 14. URL-encoded chars
        (
            1
            if any(
                url_lower.endswith(tld)
                for tld in [
                    ".tk",
                    ".ml",
                    ".cf",
                    ".gq",
                    ".ru",
                    ".xyz",
                    ".online",
                    ".site",
                    ".club",
                    ".info",
                    ".pro",
                    ".live",
                    ".store",
                    ".buzz",
                ]
            )
            else 0
        ),  # 15. suspicious TLD
    ]


# Build feature matrix
X_struct = np.array([extract_features(u) for u in df["url"]], dtype=float)

# TF-IDF on character n-grams (3-5) — excellent for URL phishing
vectorizer = TfidfVectorizer(
    analyzer="char_wb", ngram_range=(3, 5), max_features=3000, sublinear_tf=True
)
X_tfidf = vectorizer.fit_transform(df["url"])

# Hybrid: TF-IDF + structural
X = hstack([X_tfidf, csr_matrix(X_struct)])
y = df["label"].values

print(f"Feature matrix shape: {X.shape}")


# ─────────────────────────────────────────────
# TRAIN / TEST SPLIT
# ─────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)


# ─────────────────────────────────────────────
# BASE MODELS
# ─────────────────────────────────────────────
lr = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
rf = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42)
svm = SVC(kernel="rbf", probability=True, C=1.0, random_state=42)


# ─────────────────────────────────────────────
# ENSEMBLE MODELS
# ─────────────────────────────────────────────
ensemble_soft = VotingClassifier(
    estimators=[("lr", lr), ("rf", rf), ("svm", svm)],
    voting="soft",
)

ensemble_hard = VotingClassifier(
    estimators=[("lr", lr), ("rf", rf), ("svm", svm)],
    voting="hard",
)


# ─────────────────────────────────────────────
# TRAIN & EVALUATE
# ─────────────────────────────────────────────
print("\n--- Training Soft Voting Ensemble ---")
ensemble_soft.fit(X_train, y_train)
y_pred_soft = ensemble_soft.predict(X_test)
soft_acc = accuracy_score(y_test, y_pred_soft)
soft_prec = precision_score(y_test, y_pred_soft)
soft_rec = recall_score(y_test, y_pred_soft)
soft_f1 = f1_score(y_test, y_pred_soft)
cv_soft = cross_val_score(ensemble_soft, X, y, cv=5).mean()

print(f"  Accuracy : {soft_acc*100:.2f}%")
print(f"  Precision: {soft_prec*100:.2f}%")
print(f"  Recall   : {soft_rec*100:.2f}%")
print(f"  F1 Score : {soft_f1*100:.2f}%")
print(f"  CV Score : {cv_soft*100:.2f}%")

print("\n--- Training Hard Voting Ensemble ---")
ensemble_hard.fit(X_train, y_train)
y_pred_hard = ensemble_hard.predict(X_test)
hard_acc = accuracy_score(y_test, y_pred_hard)
hard_prec = precision_score(y_test, y_pred_hard)
hard_rec = recall_score(y_test, y_pred_hard)
hard_f1 = f1_score(y_test, y_pred_hard)
cv_hard = cross_val_score(ensemble_hard, X, y, cv=5).mean()

print(f"  Accuracy : {hard_acc*100:.2f}%")
print(f"  Precision: {hard_prec*100:.2f}%")
print(f"  Recall   : {hard_rec*100:.2f}%")
print(f"  F1 Score : {hard_f1*100:.2f}%")
print(f"  CV Score : {cv_hard*100:.2f}%")

print("\n--- Detailed Classification Report (Soft) ---")
print(classification_report(y_test, y_pred_soft, target_names=["Safe", "Phishing"]))


# ─────────────────────────────────────────────
# SAVE MODELS
# ─────────────────────────────────────────────
out_dir = os.path.join(os.path.dirname(__file__), "..", "app", "models")
os.makedirs(out_dir, exist_ok=True)

joblib.dump((ensemble_soft, vectorizer), os.path.join(out_dir, "ensemble_soft.pkl"))
joblib.dump((ensemble_hard, vectorizer), os.path.join(out_dir, "ensemble_hard.pkl"))
# Save standalone vectorizer + extract_features metadata for app.py
joblib.dump(vectorizer, os.path.join(out_dir, "vectorizer.pkl"))

print(f"\n✅ Models saved to {os.path.abspath(out_dir)}")
