from __future__ import annotations

import base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fpdf import FPDF

from app.channels.base import ChannelAdapter
from app.config import settings
from app.shared import OutboundMessage, SendReceipt


def _pdf_safe(text: str) -> str:
    replacements = {"—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "₦": "NGN "}
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def build_receipt_pdf(reference: str, product: str, amount_ngn: float, recipient: str) -> bytes:
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _pdf_safe("HarvestOS — Receipt"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for line in (
        f"Reference: {reference}",
        f"Customer: {recipient}",
        f"Product: {product}",
        f"Amount: NGN {amount_ngn:,.2f}",
        "",
        "This receipt confirms your reservation at a verified partner dealer.",
    ):
        pdf.cell(0, 8, _pdf_safe(line), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


class SESEmailAdapter(ChannelAdapter):
    """Amazon SES outbound — verified SDK: sesv2 SendEmail (Simple) / Raw for attachments."""

    provider = "aws-ses"

    def __init__(self) -> None:
        self._client = boto3.client("sesv2", region_name=settings.region)

    def send(self, message: OutboundMessage) -> SendReceipt:
        if not message.to:
            raise RuntimeError("Email requires a recipient address")
        subject = "Your HarvestOS message"
        if message.email_type == "receipt":
            subject = "Your HarvestOS receipt"
        if message.email_type == "agreement":
            subject = "Your HarvestOS loan agreement"
        raw = self._build_mime(subject, message)
        try:
            self._client.send_email(
                FromEmailAddress=settings.ses_from_address,
                Destination={"ToAddresses": [message.to]},
                Content={"Raw": {"Data": base64.b64encode(raw).decode()}},
            )
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"SES send failed: {exc}") from exc
        return SendReceipt(
            channel=message.channel,
            to=message.to,
            text=message.text,
            provider=self.provider,
        )

    @staticmethod
    def _build_mime(subject: str, message: OutboundMessage) -> bytes:
        outer = MIMEMultipart()
        outer["Subject"] = subject
        outer["From"] = settings.ses_from_address
        outer["To"] = message.to
        outer["Date"] = formatdate(localtime=True)
        body = _pdf_safe(message.text or "Your HarvestOS update.")
        outer.attach(MIMEText(body, "plain", "utf-8"))
        for attachment in message.attachments:
            part = MIMEApplication(attachment.get("content", b""), _subtype="pdf")
            filename = attachment.get("name", "doc.pdf")
            part.add_header("Content-Disposition", "attachment", filename=filename)
            outer.attach(part)
        return outer.as_bytes()
