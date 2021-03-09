# Covid vaccinations free slots availability checker.

This script is designed to help you with free vaccination slots checking in Slovakia. As the official [page](https://www.old.korona.gov.sk/covid-19-vaccination-form.php) is slow and from time to time not working because of huge load this script call direct API endpoint to get data.

You can edit multiple variables inside the script to fit you needs. You can also use different SMTP server.

## Install dependencies
You need to install some python modules
```bash
$ python3 -m venv venv
$ . venv/bin/activate
$ pip install -r requirements.txt
```
or

```bash
$ python3 -m venv venv
$ . venv/bin/activate
$ pip install requests
```

## Run checker
As the script is reading `smtp_username` and `smpt_password` from ENV variables you need to export them
```bash
$  export SMTP_USER="username"
$  export SMTP_PASSWORD="password"
$ python3 vaccination-checker.py
```

> Mind the extra space before export command (skipping bash history)
