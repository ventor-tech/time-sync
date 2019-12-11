# TimeSync

## Production

App should be behind proxy server like Apache2 or NGINX with SSL.

### 1. NGINX config

```
server {
        server_name           your.domain.com;

        location / {
                proxy_pass        http://localhost:8000;
                proxy_set_header Host            $host;
                proxy_set_header X-Forwarded-For $remote_addr;
                proxy_set_header        X-Forwarded-Proto $scheme;
        }
}
```

### 2. Generate SSL certificate with Let's Encrypt

```
certbot --nginx
```

More details about installation here: https://certbot.eff.org/lets-encrypt/debianstretch-nginx

## Development

Create virtual environment and install dependencies:

```
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` file and optionally change parameters.

Then run app
```
flask run
```

When modify DB models there is need to migrate changes. First do:

```
flask db migrate
```

Then on server:

```
flask db upgrade
```

## Testing

To run tests:

```
pytest
```

To calculate code coverage and view report:

```bash
coverage run -m pytest
coverage report
```
