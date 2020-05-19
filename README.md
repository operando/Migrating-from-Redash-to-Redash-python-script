# Migrating from Redash to Redash python script

Migrating from Redash to Redash python script.

```
--------------            --------------
| Old Redash | → {data} → | New Redash |
--------------            --------------
```

Migrate your data using Redash API.


## Setup(Write redash_migrator.py)

- Original Redash instance URL and admin api key
- Destination Redash instance URL and admin api key
- [Optional] data sources mapping
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