from fastapi.testclient import TestClient
from app import server

def test_inventory_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'DATA', tmp_path)
    monkeypatch.setattr(server, 'DB', tmp_path / 'fridge.db')
    item = {'name':'菠菜','quantity':'一把','storage':'冷藏','delivered':'2026-11-04','expires':'2026-11-07','estimated':True}
    with TestClient(server.app) as client:
        assert client.post('/api/items', json={'items':[item]}).status_code == 200
        saved = client.get('/api/items').json()[0]
        assert saved['name'] == '菠菜' and saved['estimated'] == 1
        item['quantity'] = '半把'
        assert client.put(f"/api/items/{saved['id']}", json=item).status_code == 200
        assert client.get('/api/items').json()[0]['quantity'] == '半把'
        assert client.post(f"/api/items/{saved['id']}/handle", json={'outcome':'丢弃了','reason':'过期'}).status_code == 200
        assert client.get('/api/items').json() == []
        history = client.get('/api/history?outcome=丢弃了').json()
        assert len(history) == 1 and history[0]['reason'] == '过期'
        event = history[0]['event_id']
        assert client.put(f'/api/history/{event}', json={'outcome':'其他处理'}).status_code == 200
        assert client.get('/api/history?outcome=丢弃了').json() == []
        assert client.post(f'/api/history/{event}/restore').status_code == 200
        assert client.get('/api/items').json()[0]['quantity'] == '半把'
        assert client.get('/api/history').json() == []
        assert client.post(f"/api/items/{saved['id']}/handle", json={'outcome':'吃完了'}).status_code == 200
        with server.connect() as db:
            assert db.execute('SELECT count(*) FROM handling_events').fetchone()[0] == 2
        assert client.post('/api/items', json={'items':[dict(item, name=' ')]}).status_code == 422

def test_suggestion_model_response(tmp_path, monkeypatch):
    import httpx
    monkeypatch.setattr(server, 'DATA', tmp_path)
    monkeypatch.setattr(server, 'DB', tmp_path / 'fridge.db')
    for key, value in {'LLM_BASE_URL':'https://example.test/v1','LLM_API_KEY':'test','LLM_MODEL':'test'}.items(): monkeypatch.setenv(key,value)
    async def fake_post(self, *args, **kwargs):
        return httpx.Response(200, request=httpx.Request('POST', 'https://example.test'), json={'choices':[{'message':{'content':'{"items":[{"name":"菠菜","quantity":"1把","shelf_life_days":3}]}'}}]})
    monkeypatch.setattr(httpx.AsyncClient, 'post', fake_post)
    with TestClient(server.app) as client:
        response=client.post('/api/suggest',json={'name':'菠菜','delivered':'2026-11-04','storage':'冷藏'})
        assert response.status_code == 200
        assert response.json()['items'][0]['estimated'] is True


def test_image_date_priority_and_fallback(tmp_path, monkeypatch):
    import httpx
    import json
    monkeypatch.setattr(server, 'DATA', tmp_path)
    monkeypatch.setattr(server, 'DB', tmp_path / 'fridge.db')
    for key, value in {'LLM_BASE_URL':'https://example.test/v1','LLM_API_KEY':'test','LLM_MODEL':'test'}.items():
        monkeypatch.setenv(key, value)
    rows = [
        {'name':'菠菜', 'received_date':'2026-11-02', 'sale_date':'2026-11-01', 'shelf_life_days':3},
        {'name':'牛奶', 'received_date':None, 'sale_date':'2026-11-03', 'shelf_life_days':5},
        {'name':'鸡蛋', 'received_date':'invalid', 'sale_date':None, 'shelf_life_days':7},
        {'name':'无效估算', 'shelf_life_days':'unknown'},
    ]
    async def fake_post(self, *args, **kwargs):
        return httpx.Response(200, request=httpx.Request('POST', 'https://example.test'), json={'choices':[{'message':{'content':json.dumps({'items':rows})}}]})
    monkeypatch.setattr(httpx.AsyncClient, 'post', fake_post)
    with TestClient(server.app) as client:
        response = client.post('/api/suggest', json={'image':'data:image/png;base64,aGVsbG8=', 'delivered':'2026-11-10', 'storage':'冷藏'})
        assert response.status_code == 200
        items = response.json()['items']
        assert [(x['delivered'], x['expires'], x['date_source']) for x in items] == [
            ('2026-11-02','2026-11-05','received_date'),
            ('2026-11-03','2026-11-08','sale_date'),
            ('2026-11-10','2026-11-17','upload_date'),
        ]
        manual = client.post('/api/suggest', json={'name':'菠菜','delivered':'2026-11-08','storage':'冷藏'}).json()['items'][0]
        assert (manual['delivered'], manual['expires'], manual['date_source']) == ('2026-11-08','2026-11-11','manual')
