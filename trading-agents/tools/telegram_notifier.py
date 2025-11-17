"""
Telegram notification module for trading alerts
Sends daily analysis summaries to Telegram
"""
import os
import requests
from typing import Dict, Any, Optional


class TelegramNotifier:
    """Send trading alerts via Telegram"""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def is_configured(self) -> bool:
        """Check if Telegram is properly configured"""
        return bool(self.bot_token and self.chat_id)

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message via Telegram

        Args:
            message: Message text to send
            parse_mode: Message formatting (HTML or Markdown)

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_configured():
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }

            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return True

        except requests.exceptions.HTTPError as e:
            # Try again with plain text if HTML parsing failed
            if "Bad Request" in str(e) and parse_mode == "HTML":
                try:
                    data["parse_mode"] = ""
                    response = requests.post(url, data=data, timeout=10)
                    response.raise_for_status()
                    return True
                except:
                    pass
            print(f"⚠️  Telegram HTTP error: {e}")
            if response:
                print(f"   Response: {response.text}")
            return False
        except Exception as e:
            print(f"⚠️  Failed to send Telegram message: {e}")
            return False

    def send_daily_analysis(self, recommendations: Dict[str, Any], cost: float) -> bool:
        """
        Send formatted daily analysis via Telegram

        Args:
            recommendations: Analysis results from orchestrator
            cost: Cost of the analysis run

        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            return False

        # Build message
        message_parts = [
            "📊 <b>Daily Trading Analysis</b>",
            ""
        ]

        # Recommendations
        recs = recommendations.get('final_recommendations', [])
        if recs:
            message_parts.append(f"<b>🎯 Recommendations ({len(recs)} total):</b>")
            for i, rec in enumerate(recs, 1):
                emoji = "🔴" if rec['priority'] == "HIGH" else "🟡"
                message_parts.append(
                    f"{emoji} {i}. <b>{rec['ticker']}</b> - {rec['action']} "
                    f"({rec['confidence']}%)\n"
                    f"   {rec['reasoning'][:150]}..."
                )
            message_parts.append("")

        # Market context
        if recommendations.get('market_context_summary'):
            message_parts.append(f"<b>📈 Market:</b>")
            message_parts.append(recommendations['market_context_summary'][:200])
            message_parts.append("")

        # Portfolio health
        if recommendations.get('portfolio_health_summary'):
            message_parts.append(f"<b>💼 Portfolio:</b>")
            message_parts.append(recommendations['portfolio_health_summary'][:200])
            message_parts.append("")

        # Risk alert
        if recommendations.get('risk_alert'):
            message_parts.append(f"⚠️ <b>ALERT:</b>")
            message_parts.append(recommendations['risk_alert'][:200])
            message_parts.append("")

        # Cost
        message_parts.append(f"💰 Cost: ${cost:.4f}")

        message = "\n".join(message_parts)

        return self.send_message(message)
