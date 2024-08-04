import requests
import logging
from fastapi import FastAPI, Response
from prometheus_client import Gauge, CollectorRegistry, generate_latest
import uvicorn
app = FastAPI()

url = 'http://198.18.114.2:9090/proxies'

registry = CollectorRegistry()

fast_proxies_all = list()
normal_proxies_all = list()

def get_all_proxies():

    response = requests.get(url)
    if response.status_code == 200:
        normal_proxies = response.json()['proxies']['PROXY']['all']
        fast_proxies = response.json()['proxies']['FAST-PROXY']['all']
        return normal_proxies,fast_proxies
    else:
        logging.error('获取代理节点失败')


def is_timeseries_duplicated(registry, metric_name):
    metric_name = metric_name.split()
    return True if metric_name in registry._collector_to_names.values() else False


def set_gauge(normal_proxies,fast_proxies):
    global fast_proxies_all, normal_proxies_all
    new_fast_proxies = list()
    new_normal_proxies = list()

    for f in range(len(fast_proxies)):
        if "-" in fast_proxies[f]:
            fast_proxies[f] = fast_proxies[f].replace("-", "_")
        if not is_timeseries_duplicated(registry, f'{fast_proxies[f]}'):
            fast_proxies[f] = Gauge(f'{fast_proxies[f]}', '代理节点connection delay', registry=registry)
            new_fast_proxies.append(fast_proxies[f])
    if new_fast_proxies:
        fast_proxies_all = new_fast_proxies

    for n in range(1, len(normal_proxies)):
        if "-" in normal_proxies[n]:
            normal_proxies[n] = normal_proxies[n].replace("-", "_")
        if not is_timeseries_duplicated(registry, f'{normal_proxies[n]}'):
            normal_proxies[n] = Gauge(f'{normal_proxies[n]}', '代理节点connection delay', registry=registry)
            new_normal_proxies.append(normal_proxies[n])
    if new_normal_proxies:
        normal_proxies_all = new_normal_proxies

    return normal_proxies_all,fast_proxies_all


def get_delay(normal_proxies,fast_proxies):

        for f in range(len(fast_proxies)):
            if "_" in fast_proxies[f]._name:
                proxy_for_url  = fast_proxies[f]._name.replace("_","-")
            else:
                proxy_for_url  = fast_proxies[f]._name

            fast_proxy_url = f'{url}/{proxy_for_url}/delay?url=https://www.google.com&timeout=2000'
            response = requests.get(fast_proxy_url)

            if response.status_code == 200:
                fast_proxies[f].set(response.json()['delay'])
                #print(prometheus_client.generate_latest(fast_proxies[f]).decode('utf-8'))
            else:
                logging.error(f'访问代理{proxy_for_url}失败，请检查代理')


        for n in range(len(normal_proxies)):
            if "_" in normal_proxies[n]._name:
                proxy_for_url = normal_proxies[n]._name.replace("_","-")
            else:
                proxy_for_url = normal_proxies[n]._name

            normal_proxy_url = f'{url}/{proxy_for_url}/delay?url=https://www.google.com&timeout=2000'
            response = requests.get(normal_proxy_url)

            if response.status_code == 200:
                normal_proxies[n].set(response.json()['delay'])
                #print(prometheus_client.generate_latest(normal_proxies[n]).decode('utf-8'))
            else:
                logging.error(f'访问代理{proxy_for_url}失败，请检查代理')

        return Response(generate_latest(registry),media_type="text/plain")

@app.route('/metrics')
def get_all():
    normal_proxies, fast_proxies = get_all_proxies()
    normal_proxies_all, fast_proxies_all = set_gauge(normal_proxies, fast_proxies)
    return get_delay(normal_proxies_all, fast_proxies_all)


if __name__ == '__main__':
    #start_http_server(9090)
    uvicorn.run(app, host='0.0.0.0', port=8000)
