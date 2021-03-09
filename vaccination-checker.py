#!/usr/bin/env python3
import os
import smtplib
import socket
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from json.decoder import JSONDecodeError

import requests

URL = 'https://mojeezdravie.nczisk.sk/api/v1/web/get_all_drivein_times_vacc'

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = os.environ.get('SMTP_USER')
# You need to create application password. Don't use your gmail account
# password !!!
# link: https://security.google.com/settings/security/apppasswords
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
SENDER = 'no_replay@example.com'
# You can set more recipients
RECIPIENTS = ['john.doe@example.com', 'john.smith@example.com']

# Number of second to sleep before next check
SLEEP = 10
# Notify only if there are free slot equal or over desired threshold
THRESHOLD = 10
# Awailable regions to check:
# - Trenčiansky
# - Banskobystrický
# - Prešovský
# - Bratislavský
# - Žilinský
# - Nitriansky
# - Košický
# - Trnavský
# - Nezaradený
# Set regions you want notification to be sent if free slots available
REGIONS = ['Bratislavský', 'Nezaradený']
# In case you want to receive mail notifications set to True
NOTIFICATIONS = False


def send_notifications(regions):
    """Send notification message via defined SMTP server."""
    msg = MIMEMultipart()
    msg['Subject'] = 'Vaccinations - Free capacities by region'
    msg['From'] = SENDER
    msg['To'] = RECIPIENTS

    body = ''.join(f'{key}: {val}\n' for key, val in regions.items())
    body += '\nhttps://www.old.korona.gov.sk/covid-19-vaccination-form.php'

    # Record the MIME types of text/plain.
    msg.attach(MIMEText(body, 'plain'))

    # Send the message via SMTP server.
    try:
        mail = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=3)
        mail.ehlo()
        mail.starttls()
        mail.login(SMTP_USERNAME, SMTP_PASSWORD)
        mail.sendmail(SENDER, RECIPIENTS, msg.as_string())
    except socket.gaierror:
        print(f"[E] - Unable to connect to SMTP server '{SMTP_SERVER}'.")
        sys.exit(os.EX_CONFIG)
    except socket.timeout:
        print(f"[E] - Connection timeout for '{SMTP_SERVER}:{SMTP_PORT}'.") # noqa
        sys.exit(os.EX_CONFIG)
    except smtplib.SMTPHeloError:
        print("[E] - The server didn’t reply properly to the 'HELO' greeting.") # noqa
        sys.exit(os.EX_DATAERR)
    except smtplib.SMTPNotSupportedError:
        print("[E] - The server does not support this extension or command.") # noqa
        sys.exit(os.EX_CONFIG)
    except smtplib.SMTPAuthenticationError:
        print("[E] - The server didn’t accept the 'username/password' combination.") # noqa
        sys.exit(os.EX_CONFIG)
    except smtplib.SMTPException:
        print("[E] - No suitable authentication method was found.")
        sys.exit(os.EX_NOUSER)
    except AttributeError as e:
        print(f"[E] - Something wrong with the 'msq' object. {e}")
        sys.exit(os.EX_DATAERR)
    except RuntimeError:
        print("[E] - SSL/TLS support is not available to your Python interpreter.") # noqa
        sys.exit(os.EX_OSERR)
    else:
        mail.quit()


def main():
    """Get free slots from vaccination centers."""
    # Check SMTP username
    if not SMTP_USERNAME and NOTIFICATIONS:
        print("Can't find 'SMTP_USERNAME' in ENV variables.")
        sys.exit(os.EX_USAGE)

    # Check SMTP password
    if not SMTP_PASSWORD and NOTIFICATIONS:
        print("Can't find 'SMTP_PASSWORD' in ENV variables.")
        sys.exit(os.EX_USAGE)

    while True:
        regions = {}

        try:
            response = requests.get(URL, headers={'Accept': 'application/json'})
        except requests.exceptions.ConnectionError as e:
            print(f'[E] Connection error: {e}')
            time.sleep(10)
            continue

        if response.status_code == 200:
            notify_and_log = False
            try:
                data = response.json()
            except JSONDecodeError as e:
                print(f'[E] JSON parsing error: {e}')
                time.sleep(10)
                continue
            # Vaccination centers
            vc = data['payload']
            # Key variables from payload
            age_from = None
            age_to = None
            region_id = None
            region_name = None
            calendar = None

            for v in vc:
                free_slots = 0
                try:
                    age_from = v['age_from']
                    age_to = v['age_to']
                    region_id = v['region_id']
                    region_name = v['region_name']
                    calendar = v['calendar_data']
                except ValueError:
                    print('[E] Requested keys are missing !!!')
                    # Try next vaccination center
                    continue

                for day in calendar:
                    if day['free_capacity'] > 0:
                        free_slots += day['free_capacity']
                        notify_and_log = True

                # Add free slots to region
                try:
                    regions['Nezaradený' if not region_name else region_name] += free_slots # noqa
                except KeyError:
                    regions['Nezaradený' if not region_name else region_name] = free_slots # noqa

            if notify_and_log:
                regions_available = {k: v for k, v in regions.items() if v > 0}
                print('[I] Free slots available =>',
                        ''.join(f'{key}: {val}, ' for key, val in regions_available.items())[:-2]) # noqa
                # Only sent notfication when watched regions have some free slots
                if regions_available.keys() & REGIONS:
                    for k, v in regions_available.items():
                        if k in REGIONS and v >= THRESHOLD and NOTIFICATIONS:
                            send_notifications(regions_available)
            else:
                print('[I] No free slots available =>',
                        ''[:-1].join(f'{key}: {val}, ' for key, val in regions.items())[:-2]) # noqa

        else:
            print(f'[E] Response code: {response.status_code}f')

        time.sleep(SLEEP)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('\n...Interrupted')
