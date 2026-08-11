import os
import time
import base64
import hmac
import hashlib
import struct
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

def send_email_qr(recipient_email, qr_url, secret):
    if not config.SMTP_PASSWORD: 
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Kode QR Google Authenticator - TRENDORA"
    msg["From"] = f"TRENDORA Security <{config.SMTP_EMAIL}>"
    msg["To"] = recipient_email
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #333; background-color: #0f1524; color: #fff; border-radius: 10px;">
      <h2 style="color: #ec4899; text-align: center;">Reset 2FA Google Authenticator</h2>
      <p style="color: #d1d5db;">Silakan scan QR Code di bawah ini menggunakan aplikasi Google Authenticator:</p>
      <div style="text-align: center; margin: 20px 0;"><img src="{qr_url}" alt="QR Code" width="200" height="200"></div>
      <p style="color: #d1d5db; text-align: center;">Kunci manual: <strong>{secret}</strong></p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)
        server.sendmail(config.SMTP_EMAIL, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

def generate_base32_secret():
    bytes_secret = os.urandom(10)
    return base64.b32encode(bytes_secret).decode('utf-8').replace('=', '')

def get_totp_token(secret, intervals_no=None):
    if intervals_no is None: 
        intervals_no = int(time.time()) // 30
    missing_padding = len(secret) % 8
    if missing_padding != 0: 
        secret += '=' * (8 - missing_padding)
    key = base64.b32decode(secret, casefold=True)
    msg = struct.pack(">Q", intervals_no)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[19] & 15
    h = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
    return str(h).zfill(6)

def verify_totp(secret, token):
    if not secret or not token: 
        return False
    curr_interval = int(time.time()) // 30
    for delta in [-1, 0, 1]:
        if get_totp_token(secret, curr_interval + delta) == str(token).strip():
            return True
    return False