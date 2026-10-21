"""Run from project root, after filling .env; never prints secret values."""
from pathlib import Path
from urllib.parse import urlparse
values={}
for line in Path('.env').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        k,v=line.split('=',1);values[k]=v
errors=[]
for k in ('ADMIN_TOKEN','RECEIPT_SECRET','POSTGRES_PASSWORD'):
    v=values.get(k,'')
    if len(v)<32 or v.startswith('replace-'): errors.append(k+': use a random secret of at least 32 characters')
if values.get('ADMIN_TOKEN')==values.get('RECEIPT_SECRET'): errors.append('Use distinct secrets')
for k in ('WEB_DOMAIN','API_DOMAIN'):
    v=values.get(k,'')
    if '.' not in v or '/' in v: errors.append(k+': specify a real DNS hostname')
if values.get('CORS_ORIGINS')!='https://'+values.get('WEB_DOMAIN',''): errors.append('CORS_ORIGINS must match HTTPS web domain')
if values.get('NEXT_PUBLIC_API_URL')!='https://'+values.get('API_DOMAIN',''): errors.append('NEXT_PUBLIC_API_URL must match HTTPS API domain')
if errors:
    raise SystemExit('Preflight failed:\n'+'\n'.join(errors))
print('Configuration preflight passed. DNS, network, backups and provider access still require deployment verification.')
