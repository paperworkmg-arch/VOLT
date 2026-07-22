import imaplib, email, os
from dotenv import load_dotenv
load_dotenv()
def get_emails():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(os.getenv("EMAIL_USER", "placeholder"), os.getenv("EMAIL_PASS", "placeholder"))
    mail.select("inbox")
    status, messages = mail.search(None, '(UNSEEN)')
    for e_id in messages[0].split()[-10:]:
        res, msg = mail.fetch(e_id, "(RFC822)")
        for response in msg:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                subject = msg["Subject"]
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()
                with open(f"agent_email_inbox/email_{e_id.decode()}.txt", "w") as f:
                    f.write(f"Subject: {subject}\n\n{body}")
    mail.logout()
if __name__ == "__main__": get_emails()
