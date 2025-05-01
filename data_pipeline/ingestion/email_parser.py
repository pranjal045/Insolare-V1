import imaplib
import email
import os

class EmailParser:
    def __init__(self, mail_server, email_id, password):
        self.mail = imaplib.IMAP4_SSL(mail_server)
        self.mail.login(email_id, password)

    def fetch_emails(self, folder='inbox'):
        self.mail.select(folder)
        status, data = self.mail.search(None, 'ALL')
        email_ids = data[0].split()
        emails = []
        for eid in email_ids:
            status, msg_data = self.mail.fetch(eid, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])
            emails.append(msg)
        return emails

if __name__ == '__main__':
    parser = EmailParser("imap.gmail.com", os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
    emails = parser.fetch_emails()
    print(f"Fetched {len(emails)} emails.")