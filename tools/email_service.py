"""
Email Service - SMTP Email Sending

Handles:
- Sending emails via SMTP
- HTML email formatting
- Error handling and logging
"""

import os
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger("email_service")


class EmailService:
    """
    SMTP Email service for sending transactional emails.
    
    Supports:
    - OTP verification emails
    - Booking confirmation emails
    - Generic HTML emails
    """
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("SMTP_FROM", self.smtp_user)
        self.company_name = os.getenv("COMPANY_NAME", "City Health Clinic")
        
    def _is_configured(self) -> bool:
        """Check if SMTP is configured"""
        return bool(self.smtp_user and self.smtp_password)
    
    def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email body
            text_content: Plain text fallback (optional)
        
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self._is_configured():
            logger.warning(f"SMTP not configured - skipping email to {to_email}")
            return False
            
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            
            # Add plain text version if provided
            if text_content:
                text_part = MIMEText(text_content, "plain")
                msg.attach(text_part)
            
            # Add HTML version
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)
            
            # Create secure SSL context
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_otp_email(self, to_email: str, otp: str) -> bool:
        """Send OTP verification email"""
        subject = "Your Verification Code"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #002cf2; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .otp-code {{ font-size: 32px; font-weight: bold; letter-spacing: 8px; 
                           color: #002cf2; text-align: center; padding: 20px; 
                           background: white; border: 2px dashed #002cf2; margin: 20px 0; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{self.company_name}</h1>
                </div>
                <div class="content">
                    <h2>Verify Your Email</h2>
                    <p>Your verification code is:</p>
                    <div class="otp-code">{otp}</div>
                    <p>This code will expire in 5 minutes.</p>
                    <p>If you didn't request this code, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from {self.company_name}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {self.company_name}
        
        Your verification code is: {otp}
        
        This code will expire in 5 minutes.
        
        If you didn't request this code, please ignore this email.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_booking_confirmation(
        self,
        to_email: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str,
        reason: str = ""
    ) -> bool:
        """Send booking confirmation email"""
        subject = f"Appointment Confirmed - {self.company_name}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #002cf2; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .details {{ background: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                .details-row {{ display: flex; justify-content: space-between; padding: 10px 0; 
                              border-bottom: 1px solid #eee; }}
                .details-row:last-child {{ border-bottom: none; }}
                .label {{ font-weight: bold; color: #666; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
                .note {{ background: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{self.company_name}</h1>
                </div>
                <div class="content">
                    <h2>Appointment Confirmed!</h2>
                    <p>Dear {patient_name},</p>
                    <p>Your appointment has been successfully booked. Here are the details:</p>
                    
                    <div class="details">
                        <div class="details-row">
                            <span class="label">Doctor:</span>
                            <span>Dr. {doctor_name}</span>
                        </div>
                        <div class="details-row">
                            <span class="label">Date:</span>
                            <span>{appointment_date}</span>
                        </div>
                        <div class="details-row">
                            <span class="label">Time:</span>
                            <span>{appointment_time}</span>
                        </div>
                        {f'<div class="details-row"><span class="label">Reason:</span><span>{reason}</span></div>' if reason else ''}
                    </div>
                    
                    <div class="note">
                        <strong>Please note:</strong> Please arrive 15 minutes before your appointment time.
                    </div>
                    
                    <p>If you need to reschedule or cancel your appointment, please contact us.</p>
                </div>
                <div class="footer">
                    <p>Thank you for choosing {self.company_name}!</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {self.company_name}
        
        Appointment Confirmed!
        
        Dear {patient_name},
        
        Your appointment has been successfully booked:
        
        Doctor: Dr. {doctor_name}
        Date: {appointment_date}
        Time: {appointment_time}
        {f'Reason: {reason}' if reason else ''}
        
        Please arrive 15 minutes before your appointment time.
        
        Thank you for choosing {self.company_name}!
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_appointment_reminder(
        self,
        to_email: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str
    ) -> bool:
        """Send appointment reminder email"""
        subject = f"Appointment Reminder - {self.company_name}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ffc107; color: #333; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .details {{ background: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Appointment Reminder</h1>
                </div>
                <div class="content">
                    <h2>Hello {patient_name},</h2>
                    <p>This is a friendly reminder about your upcoming appointment:</p>
                    
                    <div class="details">
                        <p><strong>Doctor:</strong> Dr. {doctor_name}</p>
                        <p><strong>Date:</strong> {appointment_date}</p>
                        <p><strong>Time:</strong> {appointment_time}</p>
                    </div>
                    
                    <p>Please remember to arrive 15 minutes early.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)


# Global singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the global EmailService instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
