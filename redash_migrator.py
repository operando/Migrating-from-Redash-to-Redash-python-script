# base script
# https://gist.github.com/arikfr/e1c01f6c04d8348da52f33393b5bf65d

import json
import requests
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel("ERROR")

# The Redash instance you're copying from:
ORIGIN = ""
ORIGIN_API_KEY = ""  # admin API key

# The Redash account you're copying into:
DESTINATION = ''
DESTINATION_API_KEY = ""  # admin API key

# You need to create the data sources in advance in the destination account. Once created, update the map here:
# (origin Redash data source id -> destination Redash data source id)
DATA_SOURCES = {
}

meta = {
    # include here any users you already created in the target Redash account.
    # the key is the user id in the origin Redash instance. make sure to include the API key, as it used to recreate any objects
    # this user might have owned
    "queries": {},
    "visualizations": {},
    "dashboards": {}
}


def auth_headers(api_key):
    return {
        "Authorization": "Key {}".format(api_key)
    }


def api_request(api):
    response = requests.get(ORIGIN + api, headers=auth_headers(ORIGIN_API_KEY))
    response.raise_for_status()

    return response.json()


def import_users():
    print("Importing users...")

    users = api_request('/api/users')
    for user in users:
        print("   importing: {}".format(user['id']))
        data = {
            "name": user['name'],
            "email": user['email']
        }

        if str(user['id']) in meta['users']:
            print("    ... skipping: exists.")
            continue

        if user['email'] == 'admin':
            print("    ... skipping: admin.")
            continue

        response = requests.post(DESTINATION + '/api/users?no_invite=1',
                                 json=data, headers=auth_headers(DESTINATION_API_KEY))
        response.raise_for_status()

        new_user = response.json()
        meta['users'][user['id']] = {
            'id': new_user['id'],
            'email': new_user['email'],
            'invite_link': ""  # new_user['invite_link']
        }


def get_api_key(user_id):
    response = requests.get(DESTINATION + '/api/users/{}'.format(user_id),
                            headers=auth_headers(DESTINATION_API_KEY))
    response.raise_for_status()

    return response.json()['api_key']


def get_queries(url, api_key):
    queries = []
    headers = {'Authorization': 'Key {}'.format(api_key)}
    path = "{}/api/queries".format(url)
    has_more = True
    page = 1
    while has_more:
        response = requests.get(path, headers=headers,
                                params={'page': page, 'page_size': 200, 'order': 'created_at'}).json()
        queries.extend(response['results'])
        has_more = page * response['page_size'] + 1 <= response['count']
        page += 1

    return queries


def get_dashboards(url, api_key):
    dashboards = []
    headers = {'Authorization': 'Key {}'.format(api_key)}
    path = "{}/api/dashboards".format(url)
    has_more = True
    page = 1
    while has_more:
        response = requests.get(path, headers=headers,
                                params={'page': page, 'page_size': 100, 'order': 'created_at'}).json()
        dashboards.extend(response['results'])
        has_more = page * response['page_size'] + 1 <= response['count']
        page += 1

    return dashboards


def convert_schedule(schedule):
    if schedule is None:
        return schedule

    schedule_json = {
        'interval': None,
        'until': None,
        'day_of_week': None,
        'time': None
    }

    if ":" in schedule:
        schedule_json['interval'] = 86400
        schedule_json['time'] = schedule
    else:
        schedule_json['interval'] = schedule

    return schedule_json


def import_queries():
    print("Import queries...")

    # Depends on the Redash version running in origin, you might need to use `get_queries_old`.
    queries = get_queries(ORIGIN, ORIGIN_API_KEY)

    for i, query in enumerate(queries):
        print("   importing: {}".format(query['id']))
        data_source_id = DATA_SOURCES.get(query['data_source_id'])
        if data_source_id is None:
            print("   skipped ({})".format(data_source_id))
            continue

        if str(query['id']) in meta['queries']:
            print("   skipped - was already imported".format(data_source_id))
            continue

        data = {
            "data_source_id": data_source_id,
            "query": query['query'],
            "is_archived": query['is_archived'],
            "schedule": convert_schedule(query['schedule']),
            "description": query['description'],
            "name": query['name'],
            "options": query['options'],
            "tags": query['tags'],
        }

        response = requests.post(
            DESTINATION + '/api/queries', json=data, headers=auth_headers(DESTINATION_API_KEY))
        response.raise_for_status()

        new_query_id = response.json()['id']
        meta['queries'][query['id']] = new_query_id

        data = {
            "id": new_query_id,
            "is_draft": query['is_draft'],
        }
        response = requests.post(
            DESTINATION + '/api/queries/{}'.format(new_query_id), json=data, headers=auth_headers(DESTINATION_API_KEY))
        response.raise_for_status()


def import_visualizations():
    print("Importing visualizations...")

    for query_id, new_query_id in meta['queries'].items():
        query = api_request('/api/queries/{}'.format(query_id))
        print("   importing visualizations of: {}".format(query_id))

        min_v_id = min(map(lambda n: n['id'], query['visualizations']))
        print("visualization min id: {}".format(min_v_id))

        for i, v in enumerate(query['visualizations']):
            if str(v['id']) in meta['visualizations']:
                print("skipped - was already imported".format(v['id']))
                continue

            print("visualizations index: {}".format(i))
            # 一番idが古いtableだったら、新規じゃなくて更新。それ以外は新規
            if v['type'] == 'TABLE' and min_v_id == v['id']:

                response = requests.get(DESTINATION + '/api/queries/{}'.format(
                    new_query_id), headers=auth_headers(DESTINATION_API_KEY))
                response.raise_for_status()

                new_vis = response.json()['visualizations']
                for new_v in new_vis:
                    if new_v['type'] == 'TABLE':
                        new_v_id = new_v['id']
                        print("importing table visualizations of: {}".format(new_v_id))
                        meta['visualizations'][v['id']] = new_v_id
                        data = {
                            "name": v['name'],
                            "description": v['description'],
                            "options": v['options'],
                            "type": v['type'],
                            "id": new_v_id,
                            "query_id": new_query_id,
                        }
                        response = requests.post(
                            DESTINATION + '/api/visualizations/{}'.format(new_v_id), json=data,
                            headers=auth_headers(DESTINATION_API_KEY))
                        response.raise_for_status()
            else:
                if str(v['id']) in meta['visualizations']:
                    continue

                data = {
                    "name": v['name'],
                    "description": v['description'],
                    "options": v['options'],
                    "type": v['type'],
                    "query_id": new_query_id
                }
                response = requests.post(
                    DESTINATION + '/api/visualizations', json=data, headers=auth_headers(DESTINATION_API_KEY))
                response.raise_for_status()

                meta['visualizations'][v['id']] = response.json()['id']


def import_dashboards():
    print("Importing dashboards...")

    # laod all dashboard
    dashboards = get_dashboards(ORIGIN, ORIGIN_API_KEY)

    for dashboard in dashboards:
        print("   importing: {}".format(dashboard['slug']))
        # laod dashboard
        d = api_request('/api/dashboards/{}'.format(dashboard['slug']))
        # create dashboard
        data = {'name': d['name']}
        response = requests.post(
            DESTINATION + '/api/dashboards', json=data, headers=auth_headers(DESTINATION_API_KEY))
        response.raise_for_status()

        new_dashboard = response.json()
        new_dashboard_id = new_dashboard['id']
        requests.post(
            DESTINATION + '/api/dashboards/{}'.format(new_dashboard_id), json={'is_draft': False, 'tags': d['tags']},
            headers=auth_headers(DESTINATION_API_KEY))

        # recreate widget
        for widget in d['widgets']:
            row_index = 0
            col_index = 0

            data = {
                'dashboard_id': new_dashboard_id,
                'options': widget['options'],
                'width': widget['width'],
                'text': widget['text'],
                'visualization_id': None
            }

            if not isinstance(widget['options'], dict):
                widget['options'] = {}

            if 'position' not in widget['options']:
                widget['options']['position'] = {
                    'sizeX': 3,
                    'sizeY': 8,
                    'row': row_index,
                    'col': col_index
                }

                row_index += 8
                col_index += 4

            if 'visualization' in widget:
                data['visualization_id'] = meta['visualizations'].get(
                    str(widget['visualization']['id']))

                # To remain backward compatible table visualizations need to set autoHeight...
                # if data['visualization_id'] in non_tables:
                #    widget['options']['position']['autoHeight'] = True

            if 'visualization' in widget and not data['visualization_id']:
                print('skipping for missing viz')
                continue

            response = requests.post(
                DESTINATION + '/api/widgets', json=data, headers=auth_headers(DESTINATION_API_KEY))
            response.raise_for_status()

            meta['dashboards'][d['id']] = new_dashboard_id


def save_meta():
    print("Saving meta...")
    with open('meta.json', 'w') as f:
        json.dump(meta, f)


def import_all():
    try:
        # If you had an issue while running this the first time, fixed it and running again, uncomment the following to skip content already imported.
        with open('meta.json') as f:
            meta.update(json.load(f))
        # import_users()
        import_queries()
        import_visualizations()
        import_dashboards()
    except Exception as ex:
        logging.exception(ex)

    save_meta()


if __name__ == '__main__':
    import_all()
