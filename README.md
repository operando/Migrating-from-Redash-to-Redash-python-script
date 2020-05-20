# Migrating from Redash to Redash python script

Migrating from Redash to Redash python script.

```
--------------            --------------
| Old Redash | → {data} → | New Redash |
--------------            --------------
```

Migrate your data using Redash API.

Release info(Japanese) https://note.com/operando_os/n/n8bfa8e32a694


## Setup(Write redash_migrator.py)

- Original Redash instance URL and admin api key
- Destination Redash instance URL and admin api key
- Data sources mapping
  - origin Redash data source id -> destination Redash data source id


## Run

Python 3.x

```
python redash_migrator.py
```


## Migrating support data

- queries
- visualizations
- dashboards
- users
  - default disable


## Base script

https://gist.github.com/arikfr/e1c01f6c04d8348da52f33393b5bf65d


## Achievement

- transition from Redash 6.0.0+b8536 to Redash 8.0.0+b32245