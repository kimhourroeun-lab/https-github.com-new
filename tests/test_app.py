"""Phase-1 tests use temporary local data, never the user's wardrobe DB."""
import io
import sqlite3
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import db as store
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB_PATH', tmp_path / 'data' / 'test.sqlite3')
    monkeypatch.setattr(store, 'UPLOADS_PATH', tmp_path / 'photos')
    store.init_db()
    with TestClient(app) as client:
        yield client


def test_empty_wardrobe_seed_and_layout(client):
    dashboard = client.get('/api/bootstrap').json()
    assert dashboard['total'] == 0
    assert dashboard['wardrobe']['code'] == 'W01'
    assert len(dashboard['compartments']) == 9
    assert [c['code'] for c in dashboard['compartments']] == ['A1','B1','C1','A2','B2','C2','A3','B3','C3']
    assert sum(c['item_count'] for c in dashboard['compartments']) == 0


def test_create_edit_move_delete_and_history(client):
    bootstrap = client.get('/api/bootstrap').json()
    a2 = next(c['id'] for c in bootstrap['compartments'] if c['code']=='A2')
    b2 = next(c['id'] for c in bootstrap['compartments'] if c['code']=='B2')
    response=client.post('/api/garments', data={'name':'White shirt','category':'shirt','compartment_id':str(a2),'color':'White','tag_id':'RFID0001'})
    assert response.status_code == 201, response.text
    garment_id = response.json()['id']
    assert response.json()['compartment_code'] == 'A2'
    assert client.get('/api/bootstrap').json()['categories']['shirt'] == 1
    assert client.get('/api/bootstrap').json()['total'] == 1
    response=client.put(f'/api/garments/{garment_id}',data={'name':'Formal shirt','category':'shirt','compartment_id':str(b2),'size':'M','tag_id':'RFID0001'})
    assert response.status_code == 200, response.text
    assert response.json()['compartment_code'] == 'B2'
    assert client.get('/api/bootstrap').json()['compartments'][4]['item_count'] == 1
    history=client.get('/api/history').json()
    assert len(history) == 2
    assert history[0]['from_code']=='A2' and history[0]['to_code']=='B2'
    assert client.get('/api/garments', params={'search':'formal'}).json()[0]['id'] == garment_id
    assert client.get('/api/garments', params={'compartment':str(b2)}).json()[0]['id'] == garment_id
    assert client.delete(f'/api/garments/{garment_id}').status_code == 200
    assert client.get('/api/bootstrap').json()['total'] == 0
    assert client.get('/api/history').json() == []


def test_duplicate_tag_and_invalid_compartment(client):
    assert client.post('/api/garments',data={'name':'One','category':'shirt','tag_id':'R1'}).status_code == 201
    assert client.post('/api/garments',data={'name':'Two','category':'shirt','tag_id':'R1'}).status_code == 409
    assert client.post('/api/garments',data={'name':'Three','category':'shirt','compartment_id':'9999'}).status_code == 422
    assert client.post('/api/garments',data={'name':'Four','category':'invalid'}).status_code == 422
    assert client.get('/api/bootstrap').json()['total'] == 1


def test_settings_and_backup(client):
    assert client.patch('/api/wardrobe', json={'name':'Family Closet', 'location':'Main Bedroom'}).status_code == 200
    dashboard=client.get('/api/bootstrap').json()
    assert dashboard['wardrobe']['location']=='Main Bedroom'
    first=dashboard['compartments'][0]
    r=client.patch(f"/api/compartments/{first['id']}",json={'label':'Top drawer','kind':'drawer'})
    assert r.status_code==200 and r.json()['kind']=='drawer'
    with zipfile.ZipFile(io.BytesIO(client.get('/api/backup').content)) as z:
        assert 'data/wardrobe.sqlite3' in z.namelist()
        assert 'RESTORE.txt' in z.namelist()
        snapshot=io.BytesIO(z.read('data/wardrobe.sqlite3'))
        assert len(snapshot.getvalue()) > 0


def test_photo_upload_media_and_delete(client, tmp_path):
    img=Image.new('RGB',(80,90),'blue')
    content=io.BytesIO();img.save(content,'PNG')
    r=client.post('/api/garments',data={'name':'Blue jacket','category':'jacket'},files={'photo':('jacket.png',content.getvalue(),'image/png')})
    assert r.status_code == 201, r.text
    item=r.json()
    assert item['photo_filename'].endswith('.jpg')
    image_result=client.get('/media/'+item['photo_filename'])
    assert image_result.status_code==200
    assert image_result.headers['content-type']=='image/jpeg'
    assert client.get('/media/../db.sqlite').status_code==404
    client.delete(f"/api/garments/{item['id']}")
    assert client.get('/media/'+item['photo_filename']).status_code==404
    r=client.post('/api/garments',data={'name':'Bad photo'},files={'photo':('bad.png',b'not image','image/png')})
    assert r.status_code==422


def test_tag_uniqueness_on_edit(client):
    a=client.post('/api/garments', data={'name':'One','tag_id':'T1'}).json()
    b=client.post('/api/garments', data={'name':'Two','tag_id':'T2'}).json()
    response=client.put(f"/api/garments/{b['id']}", data={'name':'Two','category':'shirt','tag_id':'T1'})
    assert response.status_code==409
    assert client.get('/api/garments/'+str(b['id'])).json()['tag_id']=='T2'


def test_owner_password_guard(client, monkeypatch):
    import app.main as web
    monkeypatch.setattr(web, 'OWNER_PASSWORD', 'a-safe-demo-password')
    assert client.get('/api/session').json()['authenticated'] is False
    assert client.get('/api/bootstrap').status_code == 401
    assert client.post('/api/login', json={'password':'wrong'}).status_code == 401
    assert client.post('/api/login', json={'password':'a-safe-demo-password'}).status_code == 200
    assert client.get('/api/bootstrap').status_code == 200
    assert client.post('/api/logout').status_code == 200
    assert client.get('/api/bootstrap').status_code == 401