"""SMTP delivery and HTML rendering for weekly skill reports."""

import html
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlmodel import Session

from backend.orm.models import CoachMessageStatus, CoachMessages, UserSkillReports
from backend.orm.session import db_engine


def render_weekly_report_html(report: UserSkillReports) -> str:
    skill_labels = {
        "claim": "주장",
        "evidence_relevance": "이유·근거의 적절성",
        "evidence_sufficiency": "이유·근거의 충분성",
        "counterargument": "다른 입장에 대한 고려",
        "passage_summary": "지문 요약",
    }
    scores = "".join(
        f"<tr><td style='padding:10px 0;color:#334155'>{html.escape(skill_labels.get(score.key, score.key))}</td>"
        f"<td style='padding:10px 0;text-align:right;font-weight:700;color:#4f46e5'>{score.score}/5</td></tr>"
        for score in report.skill_scores
    )
    actions = "".join(
        f"<li style='margin:8px 0'>{html.escape(action)}</li>"
        for action in report.recommended_actions
    )
    return f"""<!doctype html><html><body style='margin:0;background:#f8fafc;font-family:Arial,sans-serif;color:#0f172a'>
<main style='max-width:600px;margin:24px auto;background:#ffffff;border-radius:16px;padding:32px'>
  <p style='color:#4f46e5;font-weight:700;margin:0'>PARAGRAPHY</p>
  <h1 style='font-size:24px'>이번 주 논술 리포트</h1>
  <p style='color:#64748b'>최근 {report.review_count}개 답안의 채점 결과를 분석했어요.</p>
  <table style='width:100%;border-collapse:collapse'>{scores}</table>
  <section style='margin-top:24px;padding:16px;background:#eef2ff;border-radius:12px'>
    <h2 style='font-size:16px;margin-top:0'>이번 주 총평</h2><p>{html.escape(report.overall_skill_comment)}</p>
  </section>
  <h2 style='font-size:16px;margin-top:24px'>다음 학습 목표</h2><p>{html.escape(report.next_learning_goal)}</p>
  <h2 style='font-size:16px'>이번 주 실천하기!</h2><ul style='padding-left:20px'>{actions}</ul>
</main></body></html>"""


def _smtp_settings() -> tuple[str, int, str, str, str, bool]:
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM")
    if not all((host, username, password, sender)):
        raise RuntimeError("SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM must be configured.")
    return host, int(os.getenv("SMTP_PORT", "587")), username, password, sender, os.getenv("SMTP_USE_TLS", "true").lower() == "true"


def _deliver_email(recipient: str, title: str, content: str) -> None:
    host, port, username, password, sender, use_tls = _smtp_settings()
    message = EmailMessage()
    message["Subject"] = title
    message["From"] = formataddr(("Paragraphy", sender))
    message["To"] = recipient
    message.set_content("이번 주 논술 리포트는 HTML 메일을 지원하는 환경에서 확인해 주세요.")
    message.add_alternative(content, subtype="html")
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)


def send_weekly_report_email(message_id: UUID) -> None:
    """Background task: deliver a stored message and persist its outcome."""
    with Session(db_engine) as session:
        message = session.get(CoachMessages, message_id)
        if message is None or message.status != CoachMessageStatus.PENDING:
            return
        try:
            _deliver_email(message.recipient_email, message.title, message.content)
            message.status = CoachMessageStatus.SENT
            message.sent_at = datetime.now(tz=ZoneInfo("Asia/Seoul"))
        except Exception:
            message.status = CoachMessageStatus.FAILED
        session.add(message)
        session.commit()
