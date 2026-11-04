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
        return httpx.Response(200, request=httpx.Request('POST', 'https://example.test'), json={'choices':[{'message':{'content':'{"items":[{"name":"菠菜","quantity":"1把","expires":"2026-11-07"}]}'}}]})
    monkeypatch.setattr(httpx.AsyncClient, 'post', fake_post)
    with TestClient(server.app) as client:
        response=client.post('/api/suggest',json={'name':'菠菜','delivered':'2026-11-04','storage':'冷藏'})
        assert response.status_code == 200
        assert response.json()['items'][0]['estimated'] is True
