# otp_bot_final_v7_admin_users_ban_v5_FIXED_ADMIN_PANEL_STRICT.py
# Versión: NO ACUMULABLE, FILTRO ESTRICTO, GENERACIÓN POR NÚMEROS.

import time
import re
import threading
import imaplib
import email
from email.header import decode_header
import html
import random
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional
import datetime
import json
import os
import asyncio 
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

# ===========================
# CONFIGURACIÓN - EDITA ESTO
# ===========================
BOT_TOKEN = "8202877262:AAHglQByO4rVGxb0jFKbN7CVtATlyiII-GE"
MY_CHAT_ID = "7590578210"  # Tu ID como administrador
ADMIN_USERNAME = "@PAUBLITE_GT" # Tu username para mensajes a usuarios
DATA_FILE = "premium_keys.json" # Archivo para guardar las claves (PERSISTENCIA)

# Aquí defines las cuentas Gmail que quieres vigilar.
GMAIL_ACCOUNTS = [
    {"email": "propaublite@gmail.com", "app_password": "zczzcnpyhrzqbpgl"},
    {"email": "paublutegt@gmail.com", "app_password": "nvkvbiymuouxjmkf"},
    {"email": "paudronixpro@gmail.com", "app_password": "moyxztlqmgzjkwnq"},
    {"email": "popupa083@gmail.com", "app_password": "pcvyhpdrbrsyghok"},
    {"email": "pakistepa254@gmail.com", "app_password": "zzzhexfwvilikwwf"},
    {"email": "dluxevulucion@gmail.com", "app_password": "btyliqzmpmrqmyjo"},
    {"email": "amentos562@gmail.com", "app_password": "btyliqzmpmrqmyjo"},
    {"email": "zeilazet973@gmail.com", "app_password": "dpkjcookwynegixu"},
]

TARGET_SENDERS = [] # Si deseas filtrar, pon fragmentos aquí.

GIFS = [
    "https://images.squarespace-cdn.com/content/v1/545a70e0e4b0f1f91509cf05/08a31d15-bb80-4a97-acb9-7e4841badeeb/emmatest.GIF",
    "https://i.pinimg.com/originals/4f/f8/9d/4ff89d84afdadc0e47f92999725c86f7.gif",
    "https://64.media.tumblr.com/abcd41beaf505eb863d0a1e7446d779b/3d8fefbf3d6095f6-53/s540x810/4fa516adad5b78399d59c77c346997bb9a3e96a9.gifv",
    "https://pa1.aminoapps.com/6199/4a642c15e7a0aa4af95a5495487a29f387ffbc48_hq.gif",
    "https://i.pinimg.com/originals/f5/f2/74/f5f27448c036af645c27467c789ad759.gif",
    "https://i.pinimg.com/originals/12/6b/8f/126b8f18bad751435ff017dd1658b598.gif",
    "https://i.pinimg.com/originals/4e/2a/f4/4e2af41014d87c89b468cad0080667ca.gif",
    "https://i.pinimg.com/originals/7a/97/9a/7a979a5dbeb032d65d0fd03379760c88.gif",
    "https://i.pinimg.com/originals/f7/1a/29/f71a298ba0d77cbf935166da99a9f759.gif",
    "https://i.pinimg.com/originals/1a/ea/4b/1aea4b3114c9182f18eff82670c1bf5c.gif",
]

# Índice para rotar GIFs uno por uno (no repetidos). Se mantiene en memoria durante la ejecución.
GIF_INDEX = 0
GIF_INDEX_LOCK = threading.Lock()

# ===========================
# COMPORTAMIENTO
# ===========================
ACCEPT_ANY_SENDER = True
IMAP_CHECK_INTERVAL_SECONDS = 10 # ⚡ Velocidad de revisión

# ===========================
# DEBUG / MODO PRUEBAS
# ===========================
DEBUG_SEND_ALL_UNSEEN = False
DEBUG_SEND_TO_ADMIN_ONLY = False 

# ===========================
# ESTADO Y SUSCRIPCIONES (GLOBAL)
# ===========================
SUBSCRIPTIONS = set()
SUBSCRIPTIONS_LOCK = threading.Lock()
IS_SUBSCRIBED_GLOBAL = True

# { "paublte-genX-CÓDIGO": {"chat_id": 12345, "expires_at": datetime_obj, "level": "Bronce 1", "services": ["netflix"]} }
PREMIUM_KEYS: Dict[str, Dict[str, Any]] = {}
PREMIUM_KEYS_LOCK = threading.Lock()

# { chat_id: "paublte-genX-CODIGO" }
USER_ACTIVE_KEYS: Dict[int, str] = {}
USER_ACTIVE_KEYS_LOCK = threading.Lock()

# { chat_id: {"name": "User Name", "username": "@username"} }
USER_CONTACTS: Dict[int, Dict[str, str]] = {}
USER_CONTACTS_LOCK = threading.Lock()

# { chat_id } conjunto de IDs baneados
BANNED_USERS: set[int] = set()
BANNED_USERS_LOCK = threading.Lock()

ADMIN_STATE: Dict[int, str] = {}
ADMIN_BROADCAST_TARGET: Dict[int, str] = {} # chat_id -> "PREMIUM" o "NON_PREMIUM"

# ===========================
# UTILIDADES DE PERSISTENCIA
# ===========================
def load_keys():
    """Carga las claves premium, contactos y baneados desde el archivo JSON si existe."""
    global PREMIUM_KEYS, USER_ACTIVE_KEYS, SUBSCRIPTIONS, USER_CONTACTS, BANNED_USERS
    if not os.path.exists(DATA_FILE):
        print("💾 Archivo de datos no encontrado. Iniciando sin claves guardadas.")
        return
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ ERROR al leer el archivo de datos: {e}")
        return
    try:
        keys_data = data.get("keys", {})
        user_active = data.get("user_active_keys", {})
        subs = data.get("subscriptions", [])
        contacts = data.get("user_contacts", {})
        banned = data.get("banned_users", [])

        with PREMIUM_KEYS_LOCK:
            PREMIUM_KEYS = {}
            for key, details in keys_data.items():
                if isinstance(details.get("expires_at"), str):
                    try:
                        details["expires_at"] = datetime.datetime.fromisoformat(details["expires_at"])
                    except Exception:
                        details["expires_at"] = datetime.datetime.now()
                # Compatibilidad con claves antiguas
                if "services" not in details:
                    details["services"] = ["TODO"]
                PREMIUM_KEYS[key] = details

        with USER_ACTIVE_KEYS_LOCK:
            USER_ACTIVE_KEYS = {int(k): v for k, v in user_active.items()}

        with SUBSCRIPTIONS_LOCK:
            SUBSCRIPTIONS = set(subs)

        with USER_CONTACTS_LOCK:
            USER_CONTACTS = {int(k): v for k, v in contacts.items()}

        with BANNED_USERS_LOCK:
            BANNED_USERS = set(banned)

        print(f"✅ Claves, estados y baneados cargados de {DATA_FILE}. Total de claves: {len(PREMIUM_KEYS)}")
    except Exception as e:
        print(f"❌ ERROR al cargar las claves desde JSON: {e}")

def save_keys():
    """Guarda las claves premium, contactos y baneados en el archivo JSON."""
    global PREMIUM_KEYS, USER_ACTIVE_KEYS, SUBSCRIPTIONS, USER_CONTACTS, BANNED_USERS
    try:
        data_to_save = {
            "keys": {},
            "user_active_keys": {},
            "subscriptions": list(SUBSCRIPTIONS),
            "user_contacts": {},
            "banned_users": list(BANNED_USERS)
        }
        with PREMIUM_KEYS_LOCK:
            for key, details in PREMIUM_KEYS.items():
                details_copy = details.copy()
                if isinstance(details_copy.get("expires_at"), datetime.datetime):
                    details_copy["expires_at"] = details_copy["expires_at"].isoformat()
                data_to_save["keys"][key] = details_copy

        with USER_ACTIVE_KEYS_LOCK:
            data_to_save["user_active_keys"] = {str(k): v for k, v in USER_ACTIVE_KEYS.items()}

        with USER_CONTACTS_LOCK:
            data_to_save["user_contacts"] = {str(k): v for k, v in USER_CONTACTS.items()}

        with open(DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=4)
    except Exception as e:
        print(f"❌ ERROR al guardar las claves en JSON: {e}")

# ===========================
# UTILIDADES GENERALES
# ===========================
def decode_mime_words(s):
    if not s: return ""
    parts = decode_header(s)
    decoded = ""
    for part, encoding in parts:
        if isinstance(part, bytes):
            try: decoded += part.decode(encoding or "utf-8", errors="ignore")
            except: decoded += part.decode("utf-8", errors="ignore")
        else:
            decoded += part
    return decoded

def strip_html_tags(text: str) -> str:
    if not text: return ""
    text = re.sub(r'(?is)<(script|style).*?>.*?(</\1>)', ' ', text)
    text = re.sub(r'(?s)<.*?>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_sender_email(sender_raw: str) -> str:
    match = re.search(r'<(.*?)>', sender_raw)
    if match: return match.group(1).lower()
    if '@' in sender_raw: return sender_raw.lower()
    return ""

def get_time_remaining(expires_at: datetime.datetime) -> str:
    now = datetime.datetime.now()
    time_left = expires_at - now
    if time_left.total_seconds() <= 0: return "EXPIRADA"
    days = time_left.days
    hours = time_left.seconds // 3600
    minutes = (time_left.seconds % 3600) // 60
    seconds = time_left.seconds % 60
    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    if seconds > 0 or not parts: parts.append(f"{seconds}s")
    return " ".join(parts)

def update_user_contacts(user: Optional[Any], chat_id: int):
    """Actualiza la información de nombre y username de un usuario."""
    if not user: return
    user_name = user.first_name if user and user.first_name else "Usuario Desconocido"
    # Aseguramos que tenga el @ si tiene username
    user_username = f"@{user.username}" if user and user.username else "sin_username"
    with USER_CONTACTS_LOCK:
        USER_CONTACTS[chat_id] = {
            "name": user_name,
            "username": user_username
        }

# ===========================
# LÓGICA DE OTP y SERVICIOS
# ===========================
def identify_service(text: str) -> str:
    """Identifica el servicio del correo (Netflix, Disney, etc)."""
    t = text.lower()
    if "netflix" in t: return "netflix"
    if "disney" in t or "star+" in t or "espn" in t: return "disney"
    if "amazon" in t or "prime" in t: return "prime"
    if "hbo" in t or "max" in t: return "hbo"
    if "spotify" in t: return "spotify"
    return "otro"

def user_allowed_service(chat_id, service_detected):
    """Verifica si el usuario tiene permiso estricto para este servicio."""
    # El admin siempre puede ver todo si está suscrito
    if str(chat_id) == MY_CHAT_ID: return True

    with USER_ACTIVE_KEYS_LOCK:
        key = USER_ACTIVE_KEYS.get(chat_id)
    if not key: return False

    with PREMIUM_KEYS_LOCK:
        details = PREMIUM_KEYS.get(key)
    if not details: return False

    allowed = details.get("services", ["TODO"])

    # Si la clave dice TODO, pasa todo.
    if "TODO" in allowed or "todo" in allowed: return True

    # Si la clave es especifica (ej: solo 'netflix'), verificamos si coincide exactamente.
    # El servicio detectado debe estar en la lista de permitidos.
    return service_detected in allowed

def is_login_otp(subject: str, body: str) -> bool:
    """
    Determina si un correo es un OTP de inicio de sesión (aceptable).
    """
    subject_low = (subject or "").lower()
    body_low = (body or "").lower()

    DENY_KEYWORDS = [
        "restablecer", "recuperar contraseña", "cambio de contraseña", "reset password",
        "reset your password", "password reset", "change password", "cambiar contraseña",
        "cambia el email", "cambio de email", "cambio de correo", "cambiar correo",
        "cambiar dirección de correo", "change email", "email change", "change of email",
        "verify email change", "verifica el correo", "verificación de correo",
        "confirmación de cambio", "confirm change", "confirm your email change",
        "confirmación de correo", "actualiza tu correo", "código para cambiar", "código de confirmación de cambio"
    ]
    ALLOW_KEYWORDS = [
        "iniciar sesión", "codigo para iniciar", "código de verificación", "login code",
        "otp", "código otp", "verification code", "spotify", "netflix", "amazon", "primevideo",
        "disney", "hbo", "apple", "playstation", "microsoft", "uber", "airbnb", "google", "github"
    ]

    for kw in DENY_KEYWORDS:
        if kw in subject_low or kw in body_low:
            return False

    for kw in ALLOW_KEYWORDS:
        if kw in subject_low or kw in body_low:
            return True

    is_amazon_mail = "amazon" in subject_low or "amazon" in body_low or "primevideo" in subject_low or "primevideo" in body_low
    if is_amazon_mail and re.search(r"(?<!\d)(\d{6})(?!\d)", body or ""):
        return True 

    if re.search(r"(?<!\d)(\d{4,5})(?!\d)", body or ""):
        return True

    return False

def extract_otp_code(text: str, subject: str = ""):
    """
    Intenta extraer el código OTP del texto.
    """
    if not text: return None
    full_text = (text + " " + (subject or "")).replace("-", " ").replace("\xa0", " ")
    full_text_low = full_text.lower()

    is_amazon = "amazon" in full_text_low or "primevideo" in full_text_low
    if is_amazon:
        match_amazon = re.search(r"(?<!\d)(\d{6})(?!\d)", full_text)
        if match_amazon:
            return match_amazon.group(1)

    match_digits_generic = re.search(r"(?<!\d)(\d{4,5})(?!\d)", full_text)
    if match_digits_generic:
        return match_digits_generic.group(1)

    pattern_keyword = re.compile(
        r"""
        (?:c[óo]digo(?:s)? | code(?:s)? | otp | pass(?:word)? | key | token)
        \s*[:=\-]?\s* ([A-Z0-9]{4,5})
        \b
        """,
        re.IGNORECASE | re.VERBOSE
    )
    match = pattern_keyword.search(full_text)
    if match:
        return match.group(1)

    match_general = re.search(r'([A-Z0-9]{4,5})', full_text, re.IGNORECASE)
    if match_general:
        return match_general.group(1)
    return None

def get_email_body(msg):
    """Extrae el cuerpo del mensaje y devuelve texto plano (sin HTML)."""
    raw = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition") or "")
            if ctype == 'text/plain' and 'attachment' not in cdisp:
                try: raw = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                except: raw = part.get_payload(decode=True).decode(errors='ignore')
                return strip_html_tags(raw)
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                try: raw = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                except: raw = part.get_payload(decode=True).decode(errors='ignore')
                return strip_html_tags(raw)
    else:
        try: raw = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
        except: raw = msg.get_payload(decode=True).decode(errors='ignore')
        return strip_html_tags(raw)
    return ""

def send_telegram_message(text: str, service_detected: str = "otro"):
    """Envía un mensaje SOLO a los usuarios con permiso para el servicio detectado."""
    with SUBSCRIPTIONS_LOCK: 
        targets = list(SUBSCRIPTIONS)
    with BANNED_USERS_LOCK:
        targets = [cid for cid in targets if cid not in BANNED_USERS]

    if DEBUG_SEND_TO_ADMIN_ONLY:
        targets = [int(MY_CHAT_ID)]

    if not targets and not DEBUG_SEND_TO_ADMIN_ONLY: 
        targets = [int(MY_CHAT_ID)]

    try:        
        for chat_id in targets:
            # -----------------------------------
            # LÓGICA DE FILTRADO ESTRICTO
            # -----------------------------------
            if not user_allowed_service(chat_id, service_detected):
                # Si el servicio detectado NO está en la key del usuario, saltamos.
                # Ejemplo: User tiene key "netflix", service_detected es "disney" -> Salta.
                continue
            # -----------------------------------

            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                data = urllib.parse.urlencode({"chat_id": int(chat_id), "text": text, "parse_mode": "HTML"}).encode("utf-8")
                req = urllib.request.Request(url, data=data)
                with urllib.request.urlopen(req, timeout=10) as response: _ = response.read().decode("utf-8")
            except Exception as inner_e:
                print(f"❌ Error al enviar mensaje a chat {chat_id}: {inner_e}")
    except Exception as e:
        print(f"❌ Error general al enviar mensajes a Telegram: {e}")

def check_for_otp_emails_for_account(account):
    email_addr = account.get("email")
    app_pass = account.get("app_password")
    PLATFORM_KEYWORDS = [
        "netflix", "spotify", "amazon", "primevideo",
        "disney", "hbo", "apple", "playstation", "microsoft",
        "uber", "airbnb", "google", "github", "paypal", "steam"
    ]
    while True:
        mail = None
        try:
            clean_expired_keys()
            save_keys()
            if not IS_SUBSCRIBED_GLOBAL:
                time.sleep(IMAP_CHECK_INTERVAL_SECONDS)
                continue
            try:
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(email_addr, app_pass)
            except Exception as e_login:
                print(f"❌ ERROR login IMAP ({email_addr}): {e_login}")
                time.sleep(60)
                continue
            mail.select("INBOX")
            status, email_ids = mail.search(None, "UNSEEN")
            email_id_list = email_ids[0].split()
            if email_id_list:
                uids_to_process = email_id_list[-50:] 
                for uid in uids_to_process:
                    try:
                        status, msg_data = mail.fetch(uid, "(RFC822)")
                        if status != 'OK' or not msg_data or not msg_data[0]: continue
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        sender_raw = msg.get("from") or ""
                        subject_raw = msg.get("subject") or "(Sin asunto)"
                        subject = decode_mime_words(subject_raw)
                        sender_full = decode_mime_words(sender_raw)
                        body = get_email_body(msg) or ""

                        sender_low = (sender_full or "").lower()
                        subject_low = (subject or "").lower()
                        body_low = (body or "").lower()

                        if not any(kw in sender_low or kw in subject_low or kw in body_low for kw in PLATFORM_KEYWORDS):
                            try:
                                mail.store(uid, "+FLAGS", "\\Seen")
                            except Exception:
                                pass
                            continue

                        # Detectar servicio
                        service_detected = identify_service(sender_full + " " + subject + " " + body)

                        otp_code = extract_otp_code(body, subject)
                        if otp_code:
                            if not is_login_otp(subject, body):
                                try:
                                    mail.store(uid, "+FLAGS", "\\Seen")
                                except Exception:
                                    pass
                                continue
                            telegram_message = (
                                f"📣 <b>NUEVO CÓDIGO OTP ({service_detected.upper()})</b> 📣\n\n"
                                f"De: <b>{html.escape(sender_full)}</b>\n"
                                f"Cuenta: <code>{html.escape(email_addr)}</code>\n"
                                f"Asunto: {html.escape(subject)}\n\n"
                                f"🔑 <b>CÓDIGO: {otp_code}</b>"
                            )
                            # Llamar a la funcion modificada con el servicio
                            send_telegram_message(telegram_message, service_detected)
                        try:
                            mail.store(uid, "+FLAGS", "\\Seen")
                        except Exception:
                            pass
                    except Exception as e_proc:
                        print(f"❌ Error procesando uid {uid} en {email_addr}: {e_proc}")
        except Exception as e:
            print(f"❌ Error general en hilo {email_addr}: {e}")
        finally:
            if mail:
                try: mail.logout()
                except: pass
            time.sleep(IMAP_CHECK_INTERVAL_SECONDS)

# ===========================
# UTILIDADES PREMIUM KEY
# ===========================
def generate_random_key(level: str) -> str:
    """Genera una clave única en formato paublte-genX-[ALFANUMERICO]."""
    prefix = "paublte-genX"
    # Limpiar level para que no rompa el string
    lvl_clean = level.replace(" ", "_")
    random_part = "".join(random.choices("0123456789ABCDEF", k=8))
    key = f"{prefix}-{lvl_clean}-{random_part}"

    with PREMIUM_KEYS_LOCK:
        while key in PREMIUM_KEYS:
            random_part = "".join(random.choices("0123456789ABCDEF", k=8))
            key = f"{prefix}-{lvl_clean}-{random_part}"
    return key

def clean_expired_keys():
    """Limpia claves expiradas y desuscribe a los usuarios afectados y guarda."""
    global PREMIUM_KEYS, USER_ACTIVE_KEYS, SUBSCRIPTIONS
    now = datetime.datetime.now()
    with PREMIUM_KEYS_LOCK:
        keys_to_remove = []
        for key, details in list(PREMIUM_KEYS.items()):
            if details["expires_at"] <= now:
                keys_to_remove.append(key)
                if details.get("chat_id"):
                    chat_id = details["chat_id"]
                    with USER_ACTIVE_KEYS_LOCK:
                        if USER_ACTIVE_KEYS.get(chat_id) == key:
                            del USER_ACTIVE_KEYS[chat_id]
                    with SUBSCRIPTIONS_LOCK:
                        if chat_id in SUBSCRIPTIONS:
                            SUBSCRIPTIONS.remove(chat_id)
                    try:
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                        data = urllib.parse.urlencode({
                            "chat_id": chat_id,
                            "text": f"🚨 Tu clave premium ha expirado: <code>{key}</code>. Contacta a {ADMIN_USERNAME}",
                            "parse_mode": "HTML",
                        }).encode("utf-8")
                        req = urllib.request.Request(url, data=data)
                        with urllib.request.urlopen(req, timeout=5) as response: _ = response.read().decode("utf-8")
                    except Exception:
                        pass
        for key in keys_to_remove:
            if key in PREMIUM_KEYS:
                del PREMIUM_KEYS[key]
    save_keys()

def key_cleaner_thread():
    """Hilo para ejecutar la limpieza de claves periódicamente."""
    while True:
        clean_expired_keys()
        time.sleep(3600)

# ===========================
# HANDLERS de Telegram
# ===========================
def get_admin_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    keyboard = []
    keyboard.append([InlineKeyboardButton("🔑 Generar Clave (con Nivel)", callback_data="admin_prompt_generate_level")])
    keyboard.append([InlineKeyboardButton("📊 Ver Claves", callback_data="admin_view_keys")])
    keyboard.append([InlineKeyboardButton("🗑️ Eliminar Clave (usar /delkey)", callback_data="admin_prompt_delete_key")])
    keyboard.append([InlineKeyboardButton("👥 Ver Usuarios", callback_data="admin_view_users")])
    keyboard.append([InlineKeyboardButton("🚫 Bloquear (Ban) Usuario (Usar /banuser)", callback_data="admin_prompt_ban_user")])
    # Botón de broadcast
    keyboard.append([InlineKeyboardButton("📢 Broadcast Multimedia", callback_data="admin_prompt_broadcast")])
    keyboard.append([InlineKeyboardButton("🔙 Volver a /start", callback_data="back_to_start")])
    return InlineKeyboardMarkup(keyboard)

def get_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    keyboard = []
    with BANNED_USERS_LOCK:
        is_banned = chat_id in BANNED_USERS
    if is_banned:
        keyboard.append([InlineKeyboardButton("🚫 Estás Bloqueado. Contacta al Admin.", url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}")])
        return InlineKeyboardMarkup(keyboard)

    with USER_ACTIVE_KEYS_LOCK:
        user_has_key = chat_id in USER_ACTIVE_KEYS
    if user_has_key:
        with SUBSCRIPTIONS_LOCK:
            if chat_id in SUBSCRIPTIONS:
                keyboard.append([InlineKeyboardButton("🔕 Desuscribirme", callback_data="unsubscribe")])
            else:
                keyboard.append([InlineKeyboardButton("🔔 Suscribirme", callback_data="subscribe")])

        # --- AQUÍ ESTÁN LOS BOTONES (1, 2, 3) ---
        keyboard.append([
            InlineKeyboardButton("🍿 Netflix", callback_data="check_netflix"),
            InlineKeyboardButton("🏰 Disney", callback_data="check_disney")
        ])
        keyboard.append([
            InlineKeyboardButton("📦 Prime Video", callback_data="check_prime")
        ])
        # ----------------------------------------

    else:
        keyboard.append([InlineKeyboardButton(f"Comprar Claves con {ADMIN_USERNAME}", url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}")])
    if str(chat_id) == MY_CHAT_ID:
        keyboard.append([InlineKeyboardButton("🛠️ Panel de Admin", callback_data="admin_panel_start")])
        if chat_id not in SUBSCRIPTIONS:
            keyboard.append([InlineKeyboardButton("🔔 Suscribirme (Admin)", callback_data="subscribe_admin")]) 
        else:
            keyboard.append([InlineKeyboardButton("🔕 Desuscribirme (Admin)", callback_data="unsubscribe_admin")])
    return InlineKeyboardMarkup(keyboard)

def get_caption_text(user: Optional[Any], chat_id: int) -> str:
    user_id = chat_id
    user_name = user.first_name if user and user.first_name else "Usuario Desconocido"
    user_username = f"@{user.username}" if user and user.username else "sin_username"
    with BANNED_USERS_LOCK:
        is_banned = chat_id in BANNED_USERS
    if is_banned:
        return f"🚫 <b>¡TU ACCESO ESTÁ BLOQUEADO!</b> 🚫\nContacta a {ADMIN_USERNAME}."
    personal_status = ""
    with SUBSCRIPTIONS_LOCK:
        personal_status = "🟢 SUSCRITO" if chat_id in SUBSCRIPTIONS else "🔴 NO SUSCRITO"
    key_status_text = ""
    active_key = None
    with USER_ACTIVE_KEYS_LOCK:
        active_key = USER_ACTIVE_KEYS.get(chat_id)
    if active_key:
        key_details = None
        with PREMIUM_KEYS_LOCK:
            key_details = PREMIUM_KEYS.get(active_key)
        if key_details:
            time_left_str = get_time_remaining(key_details["expires_at"])
            level = key_details.get("level", "N/A")
            services = key_details.get("services", ["TODO"])
            svc_str = ", ".join(services)
            key_status_text = f"\n🔑 <b>Clave Premium:</b> <code>{html.escape(active_key)}</code>\n" \
                              f"🌟 <b>Nivel:</b> {html.escape(level)}\n" \
                              f"📺 <b>Servicios:</b> {html.escape(svc_str)}\n" \
                              f"⏳ <b>Expira en:</b> {time_left_str}"
            if time_left_str == "EXPIRADA":
                 key_status_text += "\n<i>(Esta clave ha expirado.)</i>"
                 personal_status = "🔴 NO SUSCRITO (Clave Expirada)"
        else: 
            key_status_text = "\n🔑 <b>Clave Premium:</b> INVÁLIDA"
            personal_status = "🔴 NO SUSCRITO (Clave Inválida)"
    else:
        key_status_text = "\n🔑 <b>Clave Premium:</b> NO ASIGNADA"
        key_status_text += f"\n👉 Usa <code>/key [CODIGO]</code> para canjear tu clave."
    caption = (
        "📩 <b>Bienvenido a tu Bot 🤖 de Códigos OTP</b>\n\n"
        "✅ <b>VERCION 2.0 ACTUALIZADA</b>\n\n"
        "🌏 <b>PIONERO/@PAUBLITE_GT</b>\n\n"
        f"🆔 <b>Tu ID:</b> <code>{user_id}</code>\n"
        f"👤 <b>Tu Nombre:</b> {html.escape(user_name)}\n"
        f"〽 <b>Tu Username:</b> {html.escape(user_username)}\n\n"
        f"<b>Status (tú):</b> {personal_status}"
        f"{key_status_text}\n\n"
        "—\n\n"
        "🔑 <b>Controles: Bienvenid@ recuerda que este bot no envia link o codigos de restablecimiento contraseña de ser posoble puedes ser baniado version 2.0 mantemiento hecho el 09/12/2025</b>"
    )
    return caption

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user

    gif_url = None
    with GIF_INDEX_LOCK:
        global GIF_INDEX
        if GIFS:
            gif_url = GIFS[GIF_INDEX]
            GIF_INDEX = (GIF_INDEX + 1) % len(GIFS)

    update_user_contacts(user, chat_id)
    save_keys() 

    if chat_id in ADMIN_STATE: del ADMIN_STATE[chat_id]

    reply_markup = get_keyboard(chat_id)
    caption = get_caption_text(user, chat_id)

    if update.callback_query:
        if update.callback_query.data not in ["admin_panel_start", "back_to_start"]:
            try:
                await update.callback_query.edit_message_caption(
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                await update.callback_query.answer()
                return
            except Exception:
                pass

    if update.message:
        if gif_url:
            try:
                await update.message.reply_animation(gif_url, caption=caption, parse_mode="HTML", reply_markup=reply_markup)
                return
            except Exception:
                pass
        if gif_url:
            try:
                await update.message.reply_photo(gif_url, caption=caption, parse_mode="HTML", reply_markup=reply_markup)
                return
            except Exception:
                pass
        await update.message.reply_text(caption, parse_mode="HTML", reply_markup=reply_markup)

    elif update.callback_query:
        await update.callback_query.answer()
        try:
             await update.callback_query.edit_message_caption(caption=caption, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            pass

# ===========================
# PANEL DE ADMINISTRACIÓN
# ===========================

async def admin_panel_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if str(chat_id) != MY_CHAT_ID:
        if update.callback_query:
            await update.callback_query.answer("❌ No tienes permisos de administrador.", show_alert=True)
        return
    if chat_id in ADMIN_STATE: del ADMIN_STATE[chat_id]
    total_users_known = len(USER_CONTACTS)
    now = datetime.datetime.now()
    with PREMIUM_KEYS_LOCK:
        active_premium_keys_count = sum(1 for details in PREMIUM_KEYS.values() if details.get("chat_id") is not None and details["expires_at"] > now)
        total_keys = len(PREMIUM_KEYS)
    with SUBSCRIPTIONS_LOCK:
        total_subscribed = len(SUBSCRIPTIONS)
    with BANNED_USERS_LOCK:
        total_banned = len(BANNED_USERS)
    message_text = (
        "🛠️ <b>PANEL DE ADMINISTRACIÓN</b>\n\n"
        "<b>ESTADO DEL BOT:</b>\n"
        f"👥 Usuarios Registrados (usaron /start): <b>{total_users_known}</b>\n"
        f"🔔 Usuarios Suscritos (reciben OTPs): <b>{total_subscribed}</b>\n"
        f"🔑 Claves Premium Activas (Asignadas y Vigentes): <b>{active_premium_keys_count}</b>\n"
        f"📦 Claves Totales Generadas: <b>{total_keys}</b>\n"
        f"🚫 Usuarios Bloqueados (Ban): <b>{total_banned}</b>\n\n"
        "Selecciona una acción:"
    )
    reply_markup = get_admin_keyboard(chat_id)
    if update.callback_query:
        try:
            await update.callback_query.edit_message_caption(caption=message_text, parse_mode="HTML", reply_markup=reply_markup)
        except:
            await update.callback_query.message.reply_text(message_text, parse_mode="HTML", reply_markup=reply_markup)
            await update.callback_query.message.delete()
    elif update.message:
        await update.message.reply_text(message_text, parse_mode="HTML", reply_markup=reply_markup)

async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None: return
    chat_id = query.message.chat.id
    data = query.data
    if str(chat_id) != MY_CHAT_ID:
        await query.answer("❌ No tienes permisos de administrador.", show_alert=True)
        return
    await query.answer()

    if data == "admin_panel_start":
        await admin_panel_start(update, context)
        return
    if data == "back_to_start":
        await start_command(update, context)
        return

    async def safe_edit_caption(text: str, reply_markup):
        try:
            if query.message.caption != text:
                await query.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=reply_markup)
        except:
            new_msg = await query.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            await query.message.delete()

    if data == "admin_prompt_generate_level":
        ADMIN_STATE[chat_id] = "AWAITING_KEY_DURATION_LEVEL"
        text = "🔑 **Generar Clave**\n" \
               "Formato: <code>[DÍAS] [PLATAFORMA]</code>\n\n" \
               "<b>Usa números para las plataformas:</b>\n" \
               "1 = Netflix\n" \
               "2 = Disney\n" \
               "3 = Prime\n\n" \
               "Ejemplos:\n" \
               "- <code>30 1</code> (30 días solo Netflix)\n" \
               "- <code>15 2</code> (15 días solo Disney)\n" \
               "- <code>30 todo</code> (Todo desbloqueado)"
        await safe_edit_caption(text, InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancelar", callback_data="admin_panel_start")]]))
        return

    if data == "admin_view_keys":
        now = datetime.datetime.now()
        key_list_text = "📊 **Claves Generadas**\n"
        keys_sorted = sorted(PREMIUM_KEYS.items(), key=lambda item: item[1]['expires_at'], reverse=True)
        if not keys_sorted:
            key_list_text += "No hay claves generadas."
        else:
            for key, details in keys_sorted:
                time_left_str = get_time_remaining(details["expires_at"])
                level = details.get("level", "N/A")
                services = details.get("services", ["TODO"])
                svc_str = ",".join(services)
                user_id = details.get("chat_id")
                status_emoji = "🟢" if user_id else ("🔴" if time_left_str == "EXPIRADA" else "⚪")
                user_info = ""
                if user_id:
                    contact = USER_CONTACTS.get(user_id, {})
                    name = contact.get("name", "???")
                    username = contact.get("username", "???")
                    user_info = f" -> {html.escape(name)} ({html.escape(username)})"
                key_list_text += f"{status_emoji} <code>{html.escape(key)}</code>\n   Svcs: {svc_str} | Exp: {time_left_str}{user_info}\n"
                if len(key_list_text) > 4000:
                    key_list_text = key_list_text[:4000] + "\n... (Lista truncada)"
                    break
        await safe_edit_caption(key_list_text, InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Recargar", callback_data="admin_view_keys")],
            [InlineKeyboardButton("🔙 Panel Principal", callback_data="admin_panel_start")]
        ]))
        return

    if data == "admin_view_users":
        user_list_text = "👥 **Usuarios Registrados (usaron /start)**\n"
        if not USER_CONTACTS:
            user_list_text += "No hay usuarios registrados."
        else:
            for uid, details in USER_CONTACTS.items():
                name = details.get("name", "Desconocido")
                username = details.get("username", "sin_username")
                status = []
                if uid in SUBSCRIPTIONS: status.append("🔔")
                if uid in BANNED_USERS: status.append("🚫")
                if uid in USER_ACTIVE_KEYS: status.append("🔑")
                status_str = " ".join(status) if status else "⚪"
                user_list_text += f"{status_str} <b>{html.escape(name)}</b> ({html.escape(username)})\n   ID: <code>{uid}</code>\n"
                if len(user_list_text) > 4000:
                    user_list_text = user_list_text[:4000] + "\n... (Lista truncada)"
                    break
        await safe_edit_caption(user_list_text, InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Recargar", callback_data="admin_view_users")],
            [InlineKeyboardButton("🔙 Panel Principal", callback_data="admin_panel_start")]
        ]))
        return

    if data == "admin_prompt_broadcast":
        ADMIN_STATE[chat_id] = "AWAITING_BROADCAST_TARGET"
        text = "📢 **Broadcast Multimedia**\nSelecciona el grupo de usuarios al que deseas enviar el mensaje:"
        await safe_edit_caption(text, InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Usuarios Premium", callback_data="broadcast_target_PREMIUM")],
            [InlineKeyboardButton("🔔 Usuarios No Premium", callback_data="broadcast_target_NON_PREMIUM")],
            [InlineKeyboardButton("🔙 Cancelar", callback_data="admin_panel_start")]
        ]))
        return

    if data.startswith("broadcast_target_"):
        target = data.split("_")[-1]
        ADMIN_BROADCAST_TARGET[chat_id] = target
        target_name = "Usuarios Premium" if target == "PREMIUM" else "Usuarios No Premium"
        ADMIN_STATE[chat_id] = f"AWAITING_BROADCAST_CONTENT_{target}"
        text = f"📢 **Broadcast a {target_name}**\nEnvía el mensaje (texto, foto, video o GIF) que deseas difundir."
        await safe_edit_caption(text, InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancelar", callback_data="admin_panel_start")]]))
        return

    if data == "admin_prompt_delete_key":
        ADMIN_STATE[chat_id] = "AWAITING_DELETE_KEY"
        await safe_edit_caption("🗑️ **Eliminar Clave**\nUsa el comando <code>/delkey [CODIGO]</code>.", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Panel", callback_data="admin_panel_start")]]))
        return

    if data == "admin_prompt_ban_user":
        ADMIN_STATE[chat_id] = "AWAITING_BAN_USER"
        await safe_edit_caption("🚫 **Bloquear Usuario**\nUsa el comando <code>/banuser [ID]</code>.", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Panel", callback_data="admin_panel_start")]]))
        return

async def handle_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user
    if str(chat_id) == MY_CHAT_ID:
        await update.message.reply_text("⛔ El administrador no necesita canjear claves de esta forma.")
        return
    with BANNED_USERS_LOCK:
        if chat_id in BANNED_USERS:
            await update.message.reply_text("🚫 Estás bloqueado y no puedes usar esta función. Contacta al administrador.")
            return

    # --- CAMBIO IMPORTANTE: NO ACUMULABLE ---
    with USER_ACTIVE_KEYS_LOCK:
        if chat_id in USER_ACTIVE_KEYS:
            await update.message.reply_text("❌ <b>¡Ya tienes una clave activa!</b>\nLas claves no son acumulables. Espera a que termine tu suscripción actual.", parse_mode="HTML")
            return
    # ----------------------------------------

    if not context.args:
        await update.message.reply_text("🔑 Uso: <code>/key [CODIGO_PREMIUM]</code>", parse_mode="HTML")
        return
    key = context.args[0]
    with PREMIUM_KEYS_LOCK:
        key_details = PREMIUM_KEYS.get(key)
    if not key_details:
        await update.message.reply_text("❌ Clave no válida. Verifica que la hayas escrito correctamente.")
        return
    if key_details["expires_at"] <= datetime.datetime.now():
        await update.message.reply_text("❌ Esta clave ha expirado.")
        return
    if key_details.get("chat_id") and key_details["chat_id"] != chat_id:
        current_key = USER_ACTIVE_KEYS.get(chat_id)
        if current_key != key:
            await update.message.reply_text("❌ Esta clave ya ha sido canjeada por otro usuario.")
            return

    with USER_ACTIVE_KEYS_LOCK:
        USER_ACTIVE_KEYS[chat_id] = key
    with PREMIUM_KEYS_LOCK:
        PREMIUM_KEYS[key]["chat_id"] = chat_id
    with SUBSCRIPTIONS_LOCK:
        SUBSCRIPTIONS.add(chat_id)
    update_user_contacts(user, chat_id)
    save_keys()
    time_left_str = get_time_remaining(key_details["expires_at"])
    level = key_details.get("level", "N/A")
    services = key_details.get("services", ["TODO"])
    svc_str = ", ".join(services)

    await update.message.reply_text(
        f"✅ ¡Clave canjeada con éxito!\n\n"
        f"🔑 <b>Clave:</b> <code>{html.escape(key)}</code>\n"
        f"🌟 <b>Nivel:</b> {html.escape(level)}\n"
        f"📺 <b>Servicios:</b> {html.escape(svc_str)}\n"
        f"⏳ <b>Expira en:</b> {time_left_str}\n\n"
        f"🔔 **¡Estás suscrito!** Recibirás los códigos OTP de plataformas.",
        parse_mode="HTML"
    )

async def handle_banuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_chat.id) != MY_CHAT_ID:
        await update.message.reply_text("❌ Comando solo para administradores.")
        return
    if not context.args:
        await update.message.reply_text("🚫 Uso: <code>/banuser [ID_USUARIO]</code>", parse_mode="HTML")
        return
    try:
        user_id_to_ban = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID de usuario no válido. Debe ser un número.")
        return
    with BANNED_USERS_LOCK:
        BANNED_USERS.add(user_id_to_ban)
    with SUBSCRIPTIONS_LOCK:
        if user_id_to_ban in SUBSCRIPTIONS:
            SUBSCRIPTIONS.remove(user_id_to_ban)
    with USER_ACTIVE_KEYS_LOCK:
        if user_id_to_ban in USER_ACTIVE_KEYS:
            key_to_clean = USER_ACTIVE_KEYS[user_id_to_ban]
            del USER_ACTIVE_KEYS[user_id_to_ban]
            with PREMIUM_KEYS_LOCK:
                if key_to_clean in PREMIUM_KEYS:
                    PREMIUM_KEYS[key_to_clean]["chat_id"] = None
    save_keys()
    user_info = USER_CONTACTS.get(user_id_to_ban, {"name": "Desconocido", "username": ""})
    await update.message.reply_text(
        f"✅ Usuario {user_id_to_ban} (<b>{html.escape(user_info['name'])}</b>) ha sido <b>BLOQUEADO</b> (BANEADO).\n"
        "Su clave ha sido liberada y su suscripción cancelada.", 
        parse_mode="HTML"
    )

async def handle_unbanuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_chat.id) != MY_CHAT_ID:
        await update.message.reply_text("❌ Comando solo para administradores.")
        return
    if not context.args:
        await update.message.reply_text("✅ Uso: <code>/unbanuser [ID_USUARIO]</code>", parse_mode="HTML")
        return
    try:
        user_id_to_unban = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID de usuario no válido. Debe ser un número.")
        return
    with BANNED_USERS_LOCK:
        if user_id_to_unban in BANNED_USERS:
            BANNED_USERS.remove(user_id_to_unban)
            user_info = USER_CONTACTS.get(user_id_to_unban, {"name": "Desconocido", "username": ""})
            await update.message.reply_text(
                f"✅ Usuario {user_id_to_unban} (<b>{html.escape(user_info['name'])}</b>) ha sido <b>DESBLOQUEADO</b>.", 
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(f"❕ El usuario {user_id_to_unban} no estaba bloqueado.")
    save_keys()

async def handle_delkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_chat.id) != MY_CHAT_ID:
        await update.message.reply_text("❌ Comando solo para administradores.")
        return
    if not context.args:
        await update.message.reply_text("🗑️ Uso: <code>/delkey [CODIGO_PREMIUM]</code>", parse_mode="HTML")
        return
    key = context.args[0]
    key_details = None
    with PREMIUM_KEYS_LOCK:
        key_details = PREMIUM_KEYS.pop(key, None)
    if not key_details:
        await update.message.reply_text(f"❌ Clave <code>{html.escape(key)}</code> no encontrada.", parse_mode="HTML")
        return
    user_to_clean = None
    with USER_ACTIVE_KEYS_LOCK:
        for chat_id, active_key in list(USER_ACTIVE_KEYS.items()):
            if active_key == key:
                user_to_clean = chat_id
                del USER_ACTIVE_KEYS[chat_id]
                break
    if user_to_clean:
        with SUBSCRIPTIONS_LOCK:
            if user_to_clean in SUBSCRIPTIONS:
                SUBSCRIPTIONS.remove(user_to_clean)
        user_info = USER_CONTACTS.get(user_to_clean, {"name": "Usuario", "username": "sin_username"})
        try:
            await context.bot.send_message(
                chat_id=user_to_clean, 
                text=f"🚨 Aviso de administrador: Tu clave <code>{html.escape(key)}</code> ha sido eliminada por el administrador. Has sido desuscrito. Contacta a {ADMIN_USERNAME}." , 
                parse_mode="HTML"
            )
        except Exception:
            pass
        await update.message.reply_text(
            f"✅ Clave <code>{html.escape(key)}</code> (Nivel: {key_details.get('level', 'N/A')}) eliminada con éxito.\n"
            f"Usuario afectado ({user_to_clean}, <b>{html.escape(user_info['name'])}</b>) fue notificado y desuscrito.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(f"✅ Clave <code>{html.escape(key)}</code> (Nivel: {key_details.get('level', 'N/A')}) eliminada con éxito.\n(No estaba asignada a ningún usuario).", parse_mode="HTML")
    save_keys()

async def handle_admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if str(chat_id) != MY_CHAT_ID: return
    current_state = ADMIN_STATE.get(chat_id)
    text = update.message.text or ""

    if current_state == "AWAITING_KEY_DURATION_LEVEL":
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ Formato incorrecto. Debe ser: <code>[DÍAS] [1, 2 o 3]</code> (Ej: 30 1)", parse_mode="HTML")
            return
        try:
            days = int(parts[0])
            # Detectar servicios en el texto restante
            raw_services = [p.lower() for p in parts[1:]]

            allowed_services = []
            if "todo" in raw_services:
                allowed_services = ["TODO"]
            else:
                # --- CAMBIO IMPORTANTE: SOPORTE PARA NÚMEROS DE PLATAFORMA ---
                # 1 = Netflix, 2 = Disney, 3 = Prime
                if "1" in raw_services or "netflix" in raw_services: allowed_services.append("netflix")
                if "2" in raw_services or "disney" in raw_services: allowed_services.append("disney")
                if "3" in raw_services or "prime" in raw_services: allowed_services.append("prime")

                if not allowed_services: allowed_services = ["TODO"] # Fallback si no reconoce nada

            # Nombre del nivel visual
            level_name = " ".join(parts[1:])

            if days <= 0: raise ValueError
        except ValueError:
            await update.message.reply_text("❌ La duración en días no es un número entero positivo válido.", parse_mode="HTML")
            return

        new_key = generate_random_key(level_name)
        expires_at = datetime.datetime.now() + datetime.timedelta(days=days)
        with PREMIUM_KEYS_LOCK:
            PREMIUM_KEYS[new_key] = {
                "expires_at": expires_at, 
                "level": level_name, 
                "services": allowed_services,
                "chat_id": None
            }
        save_keys()
        del ADMIN_STATE[chat_id]
        await update.message.reply_text(
            f"✅ **¡Clave generada!**\n\n"
            f"🔑 Código: <code>{html.escape(new_key)}</code>\n"
            f"🌟 Nivel: <b>{html.escape(level_name)}</b>\n"
            f"📺 Servicios: {allowed_services}\n"
            f"⏳ Duración: <b>{days} días</b>\n"
            f"📅 Expira: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "Pulsa el botón para volver al Panel.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Panel Principal", callback_data="admin_panel_start")]])
        )
        return

    if current_state in ["AWAITING_BROADCAST_CONTENT_PREMIUM", "AWAITING_BROADCAST_CONTENT_NON_PREMIUM"]:
        target = ADMIN_BROADCAST_TARGET.get(chat_id)
        if not target:
            await update.message.reply_text("❌ Error: Target de broadcast no definido. Volviendo al panel.", reply_markup=get_admin_keyboard(chat_id))
            if chat_id in ADMIN_STATE: del ADMIN_STATE[chat_id]
            return
        content_message = update.message
        asyncio.create_task(perform_broadcast(context, content_message, chat_id, target))
        del ADMIN_STATE[chat_id]
        if chat_id in ADMIN_BROADCAST_TARGET: del ADMIN_BROADCAST_TARGET[chat_id]
        await update.message.reply_text(f"📢 Broadcast iniciado en segundo plano. Te notificaré cuando termine.")
        return

async def perform_broadcast(context: ContextTypes.DEFAULT_TYPE, content_message: Message, admin_chat_id: int, target_group: str):
    with SUBSCRIPTIONS_LOCK: all_subscribers = set(SUBSCRIPTIONS)
    with USER_ACTIVE_KEYS_LOCK: users_with_keys = set(USER_ACTIVE_KEYS.keys())
    with BANNED_USERS_LOCK: banned_users = set(BANNED_USERS)
    now = datetime.datetime.now()
    active_premium_keys_ids = set()
    with PREMIUM_KEYS_LOCK:
        for details in PREMIUM_KEYS.values():
            if details.get("chat_id") is not None and details["expires_at"] > now:
                active_premium_keys_ids.add(details["chat_id"])
    premium_users = [cid for cid in all_subscribers if cid in active_premium_keys_ids and cid not in banned_users]
    non_premium_users = [cid for cid in all_subscribers if cid not in active_premium_keys_ids and cid not in banned_users]
    if target_group == "PREMIUM":
        targets = [cid for cid in premium_users if cid != admin_chat_id]
        target_name = "Usuarios Premium"
    elif target_group == "NON_PREMIUM":
        targets = [cid for cid in non_premium_users if cid != admin_chat_id]
        target_name = "Usuarios No Premium"
    else:
        targets = []
        target_name = "Nadie"
    sent_count = 0
    failed_count = 0
    await context.bot.send_message(chat_id=admin_chat_id, text=f"📢 Iniciando Broadcast a <b>{len(targets)} {target_name}</b>...", parse_mode="HTML")
    for chat_id in targets:
        try:
            if content_message.photo:
                await context.bot.send_photo(chat_id=chat_id, photo=content_message.photo[-1].file_id, caption=content_message.caption_html, parse_mode="HTML")
            elif content_message.video:
                await context.bot.send_video(chat_id=chat_id, video=content_message.video.file_id, caption=content_message.caption_html, parse_mode="HTML")
            elif content_message.animation:
                await context.bot.send_animation(chat_id=chat_id, animation=content_message.animation.file_id, caption=content_message.caption_html, parse_mode="HTML")
            elif content_message.text:
                await context.bot.send_message(chat_id=chat_id, text=content_message.text_html, parse_mode="HTML")
            else:
                failed_count += 1
                continue
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed_count += 1
    await context.bot.send_message(
        chat_id=admin_chat_id, 
        text=f"✅ Broadcast Terminado ({target_name}).\nEnviados con éxito: <b>{sent_count}</b>\nFallidos: <b>{failed_count}</b>",
        parse_mode="HTML"
    )
    await context.bot.send_message(chat_id=admin_chat_id, text="Volviendo al Panel de Admin.", reply_markup=get_admin_keyboard(admin_chat_id), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None: return
    chat_id = query.message.chat.id
    user = query.from_user
    data = query.data
    with BANNED_USERS_LOCK:
        is_banned = chat_id in BANNED_USERS
    if is_banned and str(chat_id) != MY_CHAT_ID:
        await query.answer(text="🚫 Estás bloqueado y no puedes usar esta función.", show_alert=True)
        await start_command(update, context)
        return
    if data.startswith("admin_") or data.startswith("broadcast_target_"):
        await handle_admin_callbacks(update, context)
        return
    if data == "back_to_start":
        await start_command(update, context)
        return

    # RESPUESTA A LOS BOTONES NUEVOS DE SERVICIOS
    if data in ["check_netflix", "check_disney", "check_prime"]:
        svc_map = {"check_netflix": "netflix", "check_disney": "disney", "check_prime": "prime"}
        required = svc_map.get(data)
        if user_allowed_service(chat_id, required):
            await query.answer(f"✅ Tienes acceso a {required.upper()}.")
        else:
            await query.answer(f"❌ No tienes acceso a {required.upper()}.", show_alert=True)
        return

    action_feedback = ""
    status_changed = False 
    update_user_contacts(user, chat_id)
    if chat_id in ADMIN_STATE:
        del ADMIN_STATE[chat_id]
    if data == "subscribe" or data == "subscribe_admin":
        is_admin = str(chat_id) == MY_CHAT_ID
        is_premium = chat_id in USER_ACTIVE_KEYS
        if not is_premium and not is_admin:
            action_feedback = "❌ Debes canjear una clave premium con /key para suscribirte."
        else:
            with SUBSCRIPTIONS_LOCK:
                SUBSCRIPTIONS.add(chat_id)
            status_changed = True
            action_feedback = "🔔 ¡Suscripción activada! Ya puedes recibir OTPs."
            save_keys()
    elif data == "unsubscribe" or data == "unsubscribe_admin":
        with SUBSCRIPTIONS_LOCK:
            if chat_id in SUBSCRIPTIONS:
                SUBSCRIPTIONS.remove(chat_id)
                status_changed = True
                action_feedback = "🔕 Suscripción desactivada. Ya no recibirás OTPs."
                save_keys()
            else:
                action_feedback = "Ya estabas desuscrito."
    await query.answer(text=action_feedback)
    if status_changed or data in ["subscribe", "unsubscribe", "subscribe_admin", "unsubscribe_admin"]:
        reply_markup = get_keyboard(chat_id)
        caption = get_caption_text(user, chat_id)
        try:
            await query.edit_message_caption(caption=caption, parse_mode="HTML", reply_markup=reply_markup)
        except:
            await start_command(update, context)

def main() -> None:
    load_keys()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("key", handle_key_command))
    application.add_handler(CommandHandler("banuser", handle_banuser_command))
    application.add_handler(CommandHandler("unbanuser", handle_unbanuser_command))
    application.add_handler(CommandHandler("delkey", handle_delkey_command))
    admin_filter = filters.Chat(int(MY_CHAT_ID))
    application.add_handler(MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.PHOTO | filters.VIDEO | filters.ANIMATION, handle_admin_text_input, block=False))
    application.add_handler(CallbackQueryHandler(button_handler))
    print("📧 Iniciando hilos de chequeo de correo...")
    for account in GMAIL_ACCOUNTS:
        thread = threading.Thread(target=check_for_otp_emails_for_account, args=(account,))
        thread.daemon = True
        thread.start()
    print("🧹 Iniciando hilo de limpieza de claves...")
    cleaner_thread = threading.Thread(target=key_cleaner_thread)
    cleaner_thread.daemon = True
    cleaner_thread.start()
    print("🤖 Iniciando Bot de Telegram...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()