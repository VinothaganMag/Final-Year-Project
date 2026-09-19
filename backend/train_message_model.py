"""
train_message_model.py
======================
Phishing Message / SMS / Email Detection
Using TF-IDF + Logistic Regression

Run from the backend/ directory:
    python train_message_model.py
"""

import os

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import cross_val_score, train_test_split

# ─────────────────────────────────────────────
# DATASET  (120 balanced samples)
# ─────────────────────────────────────────────
PHISHING_MESSAGES = [
    "Your account has been suspended. Click here to verify: http://paypal-secure.ru",
    "Congratulations! You won $1000. Claim now at http://free-prize.tk/claim",
    "Urgent: Your bank account is locked. Login to unlock: http://banklogin.ml",
    "We detected unusual activity. Verify your identity now: http://verify-now.cf",
    "Your Netflix subscription expired. Update billing: http://netflix-billing.gq",
    "ALERT: Your Apple ID is disabled. Verify at http://apple-id-support.ru",
    "FREE Bitcoin promo! Send 0.1 BTC get 1 BTC back. Limited time offer.",
    "Your Amazon order is on hold. Confirm address: http://amazon-delivery.tk",
    "Win a free iPhone 15! Click here to enter: http://apple-giveaway.ml",
    "Verify your PayPal account to avoid suspension: http://paypal-verify.cf",
    "IRS NOTICE: You have a pending tax refund. Claim at http://irs-refund.gq",
    "Your DHL package is held at customs. Pay fee: http://dhl-customs.ru",
    "Security alert: Unknown login detected. Reset password: http://reset-now.tk",
    "Claim your exclusive crypto airdrop! Connect wallet: http://airdrop.ml",
    "MetaMask: Verify seed phrase to avoid fund loss: http://metamask-verify.cf",
    "WhatsApp Gold upgrade available. Install now: http://wa-gold.gq",
    "Chase Bank: Suspicious transfer detected. Cancel here: http://chase-alert.ru",
    "Wells Fargo: Your debit card is blocked. Activate: http://wf-card.tk",
    "Coinbase: Complete KYC to withdraw. Verify: http://coinbase-kyc.ml",
    "Binance Security: 2FA reset required. Click: http://binance-2fa.cf",
    "You have been selected for a $500 Google reward. Claim: http://google-win.gq",
    "Microsoft: Your account will be deleted in 24hrs. Respond now.",
    "Steam: Your CS:GO knife gift is waiting. Claim: http://steam-free.tk",
    "Discord Nitro FREE for 1 month. Activate: http://discord-offer.ml",
    "Urgent: Confirm your email to keep access: http://email-verify.cf",
    "Bank alert: Wire transfer of $9999 initiated. Stop it: http://bank-stop.ru",
    "You qualify for a government stimulus check. Apply: http://stimulus.gq",
    "USPS: We missed your delivery. Reschedule: http://usps-redeliver.tk",
    "FedEx: Package undeliverable. Update address: http://fedex-address.ml",
    "Your crypto wallet needs verification. Visit: http://wallet-verify.cf",
    "NFT airdrop! Free Bored Ape NFT. Connect: http://nft-mint-free.gq",
    "Elon Musk is giving away 5000 BTC. Claim: http://elon-giveaway.ru",
    "SBI Alert: Your account will be deactivated. Update KYC: http://sbi.tk",
    "HDFC: OTP required for transaction. Enter here: http://hdfc-otp.ml",
    "ICICI: Suspicious login from new device. Verify: http://icici-verify.cf",
    "Axis Bank: Reward points expiring. Redeem: http://axis-redeem.gq",
    "PayTM: Your wallet is blocked. KYC pending: http://paytm-kyc.ru",
    "Your Aadhaar card update is mandatory. Link: http://aadhaar-link.tk",
    "PAN card not linked. Tax refund blocked. Link now: http://pan-link.ml",
    "Lottery winner! You won Rs 50,00,000. Claim: http://lottery-win.cf",
    "Free recharge! Get Rs 499 talktime. Click: http://free-recharge.gq",
    "Your electricity bill is unpaid. Pay now: http://electricity-pay.ru",
    "Jio offer: 2GB/day free for 365 days. Activate: http://jio-free.tk",
    "BSNL: Your SIM will be deactivated. Verify: http://bsnl-kyc.ml",
    "Truecaller Premium FREE! Activate: http://truecaller-prime.cf",
    "Google Pay: Transaction failed. Retry: http://gpay-retry.gq",
    "PhonePe: KYC pending. Account limited: http://phonepe-kyc.ru",
    "BHIM UPI: Pin reset required. Verify: http://bhim-verify.tk",
    "Your EMI is overdue. Pay now to avoid penalty: http://emi-pay.ml",
    "Crypto pump alert! Buy MOONDOGE before 10x surge. Group: t.me/pump",
    "Exclusive investment: 50% returns guaranteed. Invest: http://invest-win.cf",
    "Police: FIR registered against your number. Clear dues: http://fine-pay.gq",
    "Customs: Your international parcel has been seized. Pay: http://customs-fee.ru",
    "Your job application accepted! Pay registration: http://job-portal.tk",
    "Online job offer: Earn Rs 5000/day from home. Apply: http://job-easy.ml",
    "Work from home! Earn $1000 daily. Join now: http://work-home.cf",
    "Your credit score is 800! Get pre-approved loan: http://loan-offer.gq",
    "Low interest personal loan approved! Claim: http://loan-now.ru",
    "Credit card cashback expiring! Redeem: http://cashback-redeem.tk",
    "Warning: Your device has virus! Download cleaner: http://remove-virus.ml",
    "Your Gmail has been hacked. Secure now: http://gmail-secure.cf",
]

SAFE_MESSAGES = [
    "Hi, are you free for lunch tomorrow?",
    "The meeting has been rescheduled to 3pm on Friday.",
    "Please review the attached report and share your feedback.",
    "Your order #12345 has been shipped and will arrive by Thursday.",
    "Team standup call at 10am. Please be on time.",
    "Happy birthday! Hope you have a wonderful day.",
    "Reminder: your dentist appointment is tomorrow at 2pm.",
    "Thanks for completing the survey. Your opinion matters to us.",
    "Can you send me the project files by end of day?",
    "The quarterly report is ready. Please find it attached.",
    "Your flight booking confirmation: PNR AB1234 on 15 Apr.",
    "Grocery list: milk, eggs, bread, coffee, bananas.",
    "The new software update is available. Please install it.",
    "Welcome to our newsletter! Click here to read the latest issue.",
    "Your library book is due on April 20th.",
    "The event starts at 6pm. Please arrive 15 minutes early.",
    "Your lease renewal is due next month. Please contact us.",
    "Class cancelled today due to faculty meeting.",
    "Your package has been delivered at the front door.",
    "Congratulations on completing the course! Your certificate is ready.",
    "Reminder: team lunch is at the Italian restaurant on Friday.",
    "Your monthly bank statement is now available in your app.",
    "The weather forecast shows rain tomorrow. Carry an umbrella.",
    "Interview scheduled for Monday at 10am via Zoom.",
    "Your subscription has been renewed for another year.",
    "New book recommendations based on your reading history.",
    "The road construction on Main Street will cause delays today.",
    "Your doctor's report is available. Please check the portal.",
    "Office will be closed on Monday for the national holiday.",
    "Your electricity bill for this month is Rs 1200.",
    "Kindly return the borrowed documents at your earliest convenience.",
    "The wifi password has been changed to NewPass2024.",
    "Your insurance policy renewal is due in 30 days.",
    "We have received your complaint and will respond within 2 days.",
    "Please confirm your attendance for the annual dinner.",
    "Your bus pass has been renewed for the next quarter.",
    "Board exam results will be announced on April 30th.",
    "Reminder to submit your tax returns before the deadline.",
    "The parcel you ordered will be delivered between 2-4pm today.",
    "Internship offer letter has been sent to your email.",
    "Your feedback form has been submitted successfully.",
    "The server maintenance will occur Sunday 2am - 4am.",
    "Salary credited for the month of March. Please check.",
    "Please complete the onboarding documents by Friday.",
    "Your GitHub pull request has been reviewed and approved.",
    "Sprint retrospective is scheduled for tomorrow at 4pm.",
    "Your performance review is next week. Please self-assess.",
    "New feature deployed to production successfully.",
    "All CI/CD checks passed. Ready to merge.",
    "Your annual leave request has been approved.",
    "The new employee handbook is available on the intranet.",
    "Coffee machine on the 3rd floor is out of order.",
    "Visitor badges will be issued at the reception desk.",
    "The project deadline has been extended by one week.",
    "Backup completed successfully. All files are secure.",
    "Your API key has been regenerated. Update your configs.",
    "Domain renewal reminder: example.com expires in 30 days.",
    "SSL certificate automatically renewed for another year.",
    "New team member Sarah joins on Monday. Please welcome her.",
    "The vendor invoice has been approved for payment.",
    "Please fill in the timesheet by 5pm today.",
]

texts = PHISHING_MESSAGES + SAFE_MESSAGES
labels = [1] * len(PHISHING_MESSAGES) + [0] * len(SAFE_MESSAGES)

print(f"Dataset: {len(texts)} samples  |  Safe={labels.count(0)}  Phishing={labels.count(1)}")

# ─────────────────────────────────────────────
# VECTORIZE
# ─────────────────────────────────────────────
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2), max_features=5000, sublinear_tf=True, stop_words="english"
)
X = vectorizer.fit_transform(texts)

# ─────────────────────────────────────────────
# TRAIN
# ─────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, labels, test_size=0.2, random_state=42, stratify=labels
)

model = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
cv = cross_val_score(model, X, labels, cv=5).mean()

print(f"\n  Accuracy : {acc*100:.2f}%")
print(f"  CV Score : {cv*100:.2f}%")
print("\n--- Classification Report ---")
print(classification_report(y_test, y_pred, target_names=["Safe", "Phishing"]))

# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
out_dir = os.path.join(os.path.dirname(__file__), "..", "app", "models")
os.makedirs(out_dir, exist_ok=True)

joblib.dump((model, vectorizer), os.path.join(out_dir, "message_model.pkl"))
print(f"\n✅ Message model saved to {os.path.abspath(out_dir)}")
