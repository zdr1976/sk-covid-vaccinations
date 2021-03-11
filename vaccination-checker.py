#!/usr/bin/env python3
import logging
import os
import smtplib
import socket
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from json.decoder import JSONDecodeError

import requests
from requests.exceptions import ConnectionError, Timeout

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


# Number of seconds to sleep before next check
SLEEP = 10
# Number of seconds to wait for response
REQUEST_TIMEOUT = 5
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

# Logger config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname).1s] %(message)s',
    datefmt='%d-%b-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)


def send_notifications(regions):
    """Send notification message via defined SMTP server."""
    msg = MIMEMultipart()
    msg['Subject'] = 'Vaccinations - Free capacities by region'
    msg['From'] = SENDER
    msg['To'] = ', '.join(RECIPIENTS)

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
        logging.error(f"Unable to connect to SMTP server '{SMTP_SERVER}'.")
    except socket.timeout:
        logging.error(f"Connection timeout for '{SMTP_SERVER}:{SMTP_PORT}'.") # noqa
    except smtplib.SMTPHeloError:
        logging.error("The server didn’t reply properly to the 'HELO' greeting.") # noqa
    except smtplib.SMTPNotSupportedError:
        logging.error("The server does not support this extension or command.") # noqa
    except smtplib.SMTPAuthenticationError:
        logging.error("The server didn’t accept the 'username/password' combination.") # noqa
    except smtplib.SMTPException:
        logging.error("No suitable authentication method was found.")
    except AttributeError as e:
        logging.error(f"Something wrong with the 'msq' object. {e}")
    except RuntimeError:
        logging.error("SSL/TLS support is not available to your Python interpreter.") # noqa
    else:
        mail.quit()


def main():
    """Get free slots from vaccination centers."""
    # Check SMTP username
    if not SMTP_USERNAME and NOTIFICATIONS:
        logging.error("Can't find 'SMTP_USERNAME' in ENV variables.")
        sys.exit(os.EX_USAGE)

    # Check SMTP password
    if not SMTP_PASSWORD and NOTIFICATIONS:
        logging.error("Can't find 'SMTP_PASSWORD' in ENV variables.")
        sys.exit(os.EX_USAGE)

    while True:
        regions = {}

        try:
            response = requests.get(
                    URL,
                    headers={'Accept': 'application/json'},
                    timeout=REQUEST_TIMEOUT
                )
        except ConnectionError as e:
            logging.error(f'Connection error: {e}')
            time.sleep(SLEEP)
            continue
        except Timeout as e:
            logging.error(f'Connection time out: {e}')
            time.sleep(SLEEP - REQUEST_TIMEOUT)
            continue

        if response.status_code == 200:
            free_capacity = False
            try:
                data = response.json()
            except JSONDecodeError as e:
                logging.error(f'JSON parsing error: {e}')
                time.sleep(SLEEP)
                continue
            # Vaccination centers
            vc = data['payload']
            # Key variables from payload
            # age_from = None
            # age_to = None
            # region_id = None
            region_name = None
            calendar = None

            for c in vc:
                free_slots = 0
                try:
                    # age_from = c['age_from']
                    # age_to = c['age_to']
                    # region_id = c['region_id']
                    region_name = c['region_name']
                    calendar = c['calendar_data']
                except ValueError:
                    logging.error('Requested keys are missing !!!')
                    # Try next vaccination center
                    continue

                for day in calendar:
                    if day['free_capacity'] > 0:
                        free_slots += day['free_capacity']
                        free_capacity = True

                # Add free slots to region
                try:
                    regions['Nezaradený' if not region_name else region_name] += free_slots # noqa
                except KeyError:
                    regions['Nezaradený' if not region_name else region_name] = free_slots # noqa

            # Sort regions by name
            regions = dict(sorted(regions.items(), key=lambda item: item[0]))

            if free_capacity:
                regions_available = {k: v for k, v in regions.items() if v > 0}
                watched_regions_available = {}
                logging.info('Free slots available => {}'.format(''.join(f'{key}: {val}, ' for key, val in regions_available.items())[:-2])) # noqa
                # Only sent notfication when watched regions have some
                # free slots
                for k, v in regions_available.items():
                    if k in REGIONS and v >= THRESHOLD:
                        watched_regions_available[k] = v
                if NOTIFICATIONS and watched_regions_available:
                    send_notifications(watched_regions_available)
            else:
                logging.info('No free slots available => {}'.format(''.join(f'{key}: {val}, ' for key, val in regions.items())[:-2])) # noqa

        else:
            logging.error(f'Response code: {response.status_code}')

        time.sleep(SLEEP)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('\n...Interrupted')
