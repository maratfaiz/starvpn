"""
Configuration loader for STAR VPN bot.
Reads all settings from environment variables (loaded from .env).
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Telegram
    telegram_api_token: str = Field(..., env="TELEGRAM_API_TOKEN")
    telegram_admin_id: int = Field(..., env="TELEGRAM_ADMIN_ID")
    bot_username: str = Field("starisvpnbot", env="BOT_USERNAME")
    support_username: str = Field("@hashprojects", env="SUPPORT_USERNAME")
    webapp_url: str = Field("", env="WEBAPP_URL")

    # CryptoPay (@CryptoBot) — оплата в USDT / TON / BTC / ETH
    cryptopay_token: str = Field("", env="CRYPTOPAY_TOKEN")

    # Database (PostgreSQL)
    sqlalchemy_database_url: str = Field(
        "postgresql+asyncpg://user:pass@db:5432/starvpn",
        env="SQLALCHEMY_DATABASE_URL"
    )

    # Marzban
    marzban_url: str = Field("http://marzban:8000", env="MARZBAN_URL")
    marzban_username: str = Field("admin", env="MARZBAN_USERNAME")
    marzban_password: str = Field("", env="MARZBAN_PASSWORD")

    # Robokassa — card payments in RUB (Visa/Mastercard/МИР)
    robokassa_merchant_id: str = Field("", env="ROBOKASSA_MERCHANT_ID")
    robokassa_password1: str = Field("", env="ROBOKASSA_PASSWORD1")  # for generating payment links
    robokassa_password2: str = Field("", env="ROBOKASSA_PASSWORD2")  # for verifying ResultURL webhooks
    robokassa_test_mode: bool = Field(False, env="ROBOKASSA_TEST_MODE")

    # ЮMoney (YooMoney) wallet — second RUB rail via Quickpay (wallet/card/SBP)
    yoomoney_wallet: str = Field("", env="YOOMONEY_WALLET")  # номер кошелька-получателя
    yoomoney_notification_secret: str = Field("", env="YOOMONEY_NOTIFICATION_SECRET")

    # Webhook server (receives Robokassa ResultURL callbacks)
    webhook_host: str = Field("0.0.0.0", env="WEBHOOK_HOST")
    webhook_port: int = Field(8080, env="WEBHOOK_PORT")

    # VPN Server info (displayed in mini-app)
    server_host: str = Field("vpn.starvpn.ru", env="SERVER_HOST")
    server_country: str = Field("Нидерланды", env="SERVER_COUNTRY")
    server_city: str = Field("Амстердам", env="SERVER_CITY")
    server_flag: str = Field("🇳🇱", env="SERVER_FLAG")
    server_port: int = Field(443, env="SERVER_PORT")
    server_sni: str = Field("www.google.com", env="SERVER_SNI")

    # Admin web panel
    admin_web_key: str = Field("", env="ADMIN_WEB_KEY")  # long random secret for web dashboard

    # Business config
    subscription_price_rub: int = Field(100, env="SUBSCRIPTION_PRICE_RUB")
    subscription_days: int = Field(30, env="SUBSCRIPTION_DAYS")
    trial_days: int = Field(2, env="TRIAL_DAYS")
    referral_commission_pct: float = Field(15.0, env="REFERRAL_COMMISSION_PCT")
    min_topup: int = Field(50, env="MIN_TOPUP")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
