# www.bovbel.com
Personal website deployment

![Deploy www.bovbel.com](https://github.com/paulbovbel/www.bovbel.com/workflows/Deploy%20www.bovbel.com/badge.svg)

## Local Development

```bash
uv sync

export RESUME_DOC_ID="your-google-doc-id"
uv run python deploy.py all
uv run pytest test.py
```

## Updating Dependencies

```bash
uv lock --upgrade
```
