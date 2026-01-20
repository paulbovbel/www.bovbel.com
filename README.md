# www.bovbel.com
Personal website deployment

![Deploy www.bovbel.com](https://github.com/paulbovbel/www.bovbel.com/workflows/Deploy%20www.bovbel.com/badge.svg)

## Local Development

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

export RESUME_DOC_ID="your-google-doc-id"
./venv/bin/python deploy.py

./venv/bin/pytest test.py -v
```

## Updating Dependencies

```bash
./venv/bin/pip install pip-tools
./venv/bin/pip-compile requirements.in
./venv/bin/pip-sync
```
