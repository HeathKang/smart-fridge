import base64
import binascii
import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from app.migrations import migrate

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
DATA = Path(os.environ.get('DATA_DIR', ROOT / 'data'))
DB = DATA / 'fridge.db'
Storage = Literal['冷藏', '冷冻', '常温']

def connect():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    return db

@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA.mkdir(parents=True, exist_ok=True)
    migrate(DB)
    yield

app = FastAPI(title='鲜知 API', lifespan=lifespan)

class Item(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: str = Field(default='', max_length=100)
    storage: Storage = '冷藏'
    delivered: date
    expires: date
    estimated: bool = False

    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        value = value.strip()
        if not value: raise ValueError('请填写食材名称')
        return value

    def values(self):
        return (self.name, self.quantity, self.storage, self.delivered.isoformat(), self.expires.isoformat(), int(self.estimated))

class ItemBatch(BaseModel):
    items: list[Item] = Field(min_length=1, max_length=100)

class Handling(BaseModel):
    outcome: Literal['吃完了', '丢弃了', '其他处理']
    reason: Literal['过期', '变质', '不想吃', '其他'] | None = None

    @field_validator('reason')
    @classmethod
    def valid_reason(cls, value, info):
        if value and info.data.get('outcome') != '丢弃了': raise ValueError('仅丢弃时可以填写原因')
        return value

class Suggestion(BaseModel):
    name: str = Field(default='', max_length=100)
    delivered: date
    storage: Storage = '冷藏'
    image: str | None = Field(default=None, max_length=8_000_100)

@app.get('/api/health')
def health():
    with connect() as db:
        db.execute('SELECT count(*) FROM items').fetchone()
        db.execute('SELECT count(*) FROM handling_events').fetchone()
    return {'status': 'ok'}

@app.get('/api/items')
def list_items():
    with connect() as db:
        return [dict(row) for row in db.execute('SELECT * FROM items WHERE NOT EXISTS (SELECT 1 FROM handling_events e WHERE e.item_id=items.id AND e.restored_at IS NULL) ORDER BY expires, id')]

@app.post('/api/items')
def add_items(batch: ItemBatch):
    with connect() as db:
        db.executemany('INSERT INTO items(name,quantity,storage,delivered,expires,estimated) VALUES(?,?,?,?,?,?)', [item.values() for item in batch.items])
    return {'ok': True}

@app.put('/api/items/{item_id}')
def update_item(item_id: int, item: Item):
    with connect() as db:
        result = db.execute('UPDATE items SET name=?,quantity=?,storage=?,delivered=?,expires=?,estimated=? WHERE id=? AND NOT EXISTS (SELECT 1 FROM handling_events e WHERE e.item_id=items.id AND e.restored_at IS NULL)', (*item.values(), item_id))
        if not result.rowcount: raise HTTPException(404, '食材不存在')
    return {'ok': True}

@app.get('/api/history')
def history(outcome: Literal['吃完了', '丢弃了', '其他处理'] | None = None, start: date | None = None, end: date | None = None):
    query = "SELECT e.id AS event_id, e.outcome, e.reason, e.handled_at, i.* FROM handling_events e JOIN items i ON i.id=e.item_id WHERE e.restored_at IS NULL"
    args = []
    if outcome: query += ' AND e.outcome=?'; args.append(outcome)
    if start: query += " AND date(e.handled_at, 'localtime') >= ?"; args.append(start.isoformat())
    if end: query += " AND date(e.handled_at, 'localtime') <= ?"; args.append(end.isoformat())
    with connect() as db:
        return [dict(row) for row in db.execute(query + ' ORDER BY e.handled_at DESC, e.id DESC', args)]

@app.post('/api/items/{item_id}/handle')
def handle_item(item_id: int, handling: Handling):
    with connect() as db:
        result = db.execute("INSERT INTO handling_events(item_id, outcome, reason, handled_at) SELECT id, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now') FROM items WHERE id=? AND NOT EXISTS (SELECT 1 FROM handling_events WHERE item_id=? AND restored_at IS NULL)", (handling.outcome, handling.reason, item_id, item_id))
        if not result.rowcount: raise HTTPException(404, '食材不存在或已处理')
    return {'ok': True}

@app.put('/api/history/{event_id}')
def correct_handling(event_id: int, handling: Handling):
    with connect() as db:
        result = db.execute('UPDATE handling_events SET outcome=?, reason=? WHERE id=? AND restored_at IS NULL', (handling.outcome, handling.reason, event_id))
        if not result.rowcount: raise HTTPException(404, '记录不存在或已恢复')
    return {'ok': True}

@app.post('/api/history/{event_id}/restore')
def restore_item(event_id: int):
    with connect() as db:
        result = db.execute("UPDATE handling_events SET restored_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND restored_at IS NULL", (event_id,))
        if not result.rowcount: raise HTTPException(404, '记录不存在或已恢复')
    return {'ok': True}

@app.post('/api/suggest')
async def suggest(data: Suggestion):
    key, base, model = (os.getenv('LLM_API_KEY', ''), os.getenv('LLM_BASE_URL', '').rstrip('/'), os.getenv('LLM_MODEL', ''))
    if not all((key, base, model)): raise HTTPException(400, '请先配置 LLM_BASE_URL、LLM_API_KEY 和 LLM_MODEL')
    prompt = f'你是食材管理助手。只返回 JSON 对象 {{"items":[{{"name":"食材名称","quantity":"数量","received_date":"YYYY-MM-DD或null","sale_date":"YYYY-MM-DD或null","shelf_life_days":整数}}]}}。逐项识别图片里明确标注的签收日期和发售日期；订单级日期适用于该订单中的所有食材，逐项填写；没有完整明确的日期时返回 null，不要编造或将其他日期当作签收日期或发售日期。按{data.storage}储存估算保守的一般可存放天数 shelf_life_days（非负整数），不要声称保证安全。识别不确定的名称照实填写，排除非食材。'
    content = [{'type': 'text', 'text': prompt}]
    if data.image:
        try:
            header, encoded = data.image.split(',', 1)
            if header not in ('data:image/jpeg;base64', 'data:image/png;base64', 'data:image/webp;base64') or len(base64.b64decode(encoded, validate=True)) > 6_000_000: raise ValueError()
        except (ValueError, binascii.Error): raise HTTPException(400, '请使用不超过 6 MB 的 JPG、PNG 或 WebP 图片')
        content.append({'type': 'image_url', 'image_url': {'url': data.image}})
    elif data.name.strip(): content.append({'type':'text', 'text':'食材：' + data.name})
    else: raise HTTPException(400, '请选择图片或填写食材名称')
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(base + '/chat/completions', headers={'Authorization':'Bearer '+key}, json={'model':model,'messages':[{'role':'user','content':content}],'temperature':0.1})
            response.raise_for_status()
        text = response.json()['choices'][0]['message']['content'].strip()
        if text.startswith('```'): text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        result = json.loads(text)['items']
        if not isinstance(result, list): raise ValueError()
        items = []
        for row in result[:100]:
            try:
                if not isinstance(row, dict):
                    continue
                shelf_life = row.get('shelf_life_days')
                if isinstance(shelf_life, bool) or not isinstance(shelf_life, int) or not 0 <= shelf_life <= 3650:
                    continue
                base_date = data.delivered
                source = 'upload_date' if data.image else 'manual'
                if data.image:
                    for field, label in (('received_date', 'received_date'), ('sale_date', 'sale_date')):
                        try:
                            candidate = date.fromisoformat(row.get(field) or '')
                        except (ValueError, TypeError):
                            continue
                        base_date, source = candidate, label
                        break
                item = Item(name=row['name'], quantity=str(row.get('quantity') or ''), storage=data.storage, delivered=base_date, expires=base_date + timedelta(days=shelf_life), estimated=True).model_dump(mode='json')
                item['date_source'] = source
                items.append(item)
            except (ValueError, KeyError, TypeError, OverflowError): continue
        return {'items': items}
    except httpx.HTTPError: raise HTTPException(502, '无法连接模型服务，请检查配置或稍后重试')
    except (ValueError, KeyError, IndexError, TypeError): raise HTTPException(502, '模型响应无法处理，请检查模型兼容性或重试')

DIST = ROOT / 'frontend' / 'dist'
if (DIST / 'assets').is_dir(): app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')
@app.get('/', include_in_schema=False)
def index():
    if not (DIST / 'index.html').exists(): raise HTTPException(503, '请先构建前端')
    return FileResponse(DIST / 'index.html')
