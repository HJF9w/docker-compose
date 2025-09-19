import imaplib
import datetime
import os
import sys

def get_env_vars_with_prefix(prefix):
    return {key: value for key, value in os.environ.items() if key.startswith(prefix)}

# Get environment variables with prefix "del_mail_script_"
env_vars = get_env_vars_with_prefix('del_mail_script_')

# Fetch required variables
imap_host = env_vars.get('del_mail_script_imap_host')
imap_user = env_vars.get('del_mail_script_imap_user')
imap_pass = env_vars.get('del_mail_script_imap_pass')
folder_name = env_vars.get('del_mail_script_folder_name', 'INBOX')  # Default
days = int(env_vars.get('del_mail_script_days', 14))
use_ssl = env_vars.get('del_mail_script_imap_ssl', 'true').lower() in ('1', 'true', 'yes')
debug = env_vars.get('del_mail_script_debug', 'false').lower() in ('1', 'true', 'yes')

# Check required variables
missing = [k for k in ['imap_host', 'imap_user', 'imap_pass'] if eval(k) is None]
if missing:
    print(f"ERROR: Missing required environment variables: {', '.join('del_mail_script_' + m for m in missing)}", file=sys.stderr)
    sys.exit(1)

if debug:
    print(f"DEBUG: Connecting to IMAP host={imap_host} port=993 ssl={use_ssl} folder={folder_name} days={days}")

# Connect to IMAP
if use_ssl:
    mail = imaplib.IMAP4_SSL(imap_host)
else:
    mail = imaplib.IMAP4(imap_host)
mail.login(imap_user, imap_pass)
mail.select(folder_name)

# Calculate threshold
threshold_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")

if debug:
    print(f"DEBUG: Threshold date for deletion: {threshold_date}")

# Search and delete old messages
result, data = mail.search(None, f'(BEFORE {threshold_date})')

if result == 'OK' and data[0]:
    messages = data[0].split()
    for msg_id in messages:
        mail.store(msg_id, '+FLAGS', '\\Deleted')
    mail.expunge()
    print(f"Deleted {len(messages)} messages older than {days} days.")
else:
    print("No messages found to delete.")

mail.close()
mail.logout()

if debug:
    print("DEBUG: IMAP logout complete")

