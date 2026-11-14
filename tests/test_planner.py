"""V1.1 regression tests. All records/photos live under pytest temporary paths."""
import copy
import io
import shutil
import sqlite3
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from app import db as store
from app.main import app

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB_PATH', tmp_path / 'test.sqlite3')
    monkeypatch.setattr(store, 'UPLOADS_PATH', tmp_path / 'photos')
    store.init_db()
    with TestClient(app) as c:
        yield c

def plan(client):
    r=client.get('/api/planner'); assert r.status_code==200
    return r.json()

def test_default_and_save_room(client):
    p=plan(client); assert len(p['compartments'])==9
    assert sum(c['w']*c['h'] for c in p['compartments'])==pytest.approx(10000)
    p['room']['name']='Master bedroom';p['room']['width']=4500
    r=client.put('/api/planner',json=p);assert r.status_code==200,r.text
    assert r.json()['revision']==1
    assert client.get('/api/bootstrap').json()['wardrobe']['location']=='Master bedroom'

def test_l_room_and_bad_wardrobe(client):
    p=plan(client);p['room']['shape']='l';p['room']['openings']=[]
    assert client.put('/api/planner',json=p).status_code==422
    p['cabinet']['x']=0;p['cabinet']['y']=0
    r=client.put('/api/planner',json=p);assert r.status_code==200,r.text
    p=r.json();p['cabinet']['height']=4000
    assert client.put('/api/planner',json=p).status_code==422
    p['cabinet']['height']=2400;p['room']['cut_width']=p['room']['width']
    assert client.put('/api/planner',json=p).status_code==422

def test_split_preserves_photo_ids_and_history(client):
    p=plan(client);c=p['compartments'][3]
    buf=io.BytesIO();Image.new('RGB',(80,120),'white').save(buf,'PNG')
    g=client.post('/api/garments',data={'name':'Original garment','compartment_id':c['id']},files={'photo':('original.png',buf.getvalue(),'image/png')}).json()
    c['w']/=2;new=dict(c,id=None,code='N1',x=c['x']+c['w'])
    p['compartments'].append(new)
    r=client.put('/api/planner',json=p);assert r.status_code==200,r.text
    assert len(r.json()['compartments'])==10
    current=client.get('/api/garments/'+str(g['id'])).json()
    assert current['compartment_id']==g['compartment_id']
    assert current['photo_filename']==g['photo_filename']
    assert client.get('/media/'+g['photo_filename']).status_code==200
    assert client.get('/api/bootstrap').json()['total']==1
    assert len(client.get('/api/history').json())==1
    store.init_db();assert len(plan(client)['compartments'])==10

def test_cannot_remove_occupied_or_history_linked_cell(client):
    p=plan(client);cid=p['compartments'][0]['id']
    g=client.post('/api/garments',data={'name':'Keep','compartment_id':cid}).json()
    p['compartments']=p['compartments'][1:]
    assert client.put('/api/planner',json=p).status_code==409
    client.patch('/api/garments/'+str(g['id'])+'/move',json={'compartment_id':None})
    assert client.put('/api/planner',json=p).status_code==409
    assert len(plan(client)['compartments'])==9

def test_removing_empty_cell_does_not_reseed(client):
    p=plan(client);p['compartments'].pop()
    assert client.put('/api/planner',json=p).status_code==200
    store.init_db();assert len(plan(client)['compartments'])==8

def test_stale_revision(client):
    p=plan(client)
    assert client.put('/api/planner',json=p).status_code==200
    assert client.put('/api/planner',json=p).status_code==409
    p=plan(client);c=p['compartments'][0]
    client.patch('/api/compartments/'+str(c['id']),json={'label':'Changed','kind':'box'})
    assert client.put('/api/planner',json=p).status_code==409

@pytest.mark.parametrize('bad', ['overlap','duplicate','outside','unknown','reserved'])
def test_reject_bad_geometry_without_writes(client,bad):
    p=plan(client);before=copy.deepcopy(p)
    if bad=='overlap':p['compartments'][0]['w']=60
    if bad=='duplicate':p['compartments'][0]['code']=p['compartments'][1]['code'].lower()
    if bad=='outside':p['compartments'][0]['x']=99
    if bad=='unknown':p['compartments'][0]['id']=99999
    if bad=='reserved':p['compartments'][0]['code']='__v11_1'
    assert client.put('/api/planner',json=p).status_code==422
    assert plan(client)==before

def test_bad_openings(client):
    p=plan(client);p['room']['openings'][0]['width']=6000
    assert client.put('/api/planner',json=p).status_code==422
    p=plan(client);p['room']['openings'].append(dict(p['room']['openings'][0]))
    assert client.put('/api/planner',json=p).status_code==422

def test_move_and_auth(client,monkeypatch):
    import app.main as web
    p=plan(client);a,b=[x['id'] for x in p['compartments'][:2]]
    g=client.post('/api/garments',data={'name':'Move me','compartment_id':a}).json()
    url='/api/garments/'+str(g['id'])+'/move'
    r=client.patch(url,json={'compartment_id':b});assert r.status_code==200
    assert r.json()['compartment_id']==b
    assert client.patch(url,json={'compartment_id':b}).status_code==200
    assert len(client.get('/api/history').json())==2
    assert client.patch(url,json={'compartment_id':99999}).status_code==422
    monkeypatch.setattr(web,'OWNER_PASSWORD','test-guard')
    assert client.get('/api/planner').status_code==401
    assert client.put('/api/planner',json=p).status_code==401
    assert client.patch(url,json={'compartment_id':a}).status_code==401
    assert client.get('/api/backup').status_code==401

def test_legacy_migration_preserves_data(client,tmp_path,monkeypatch):
    snapshot=next((store.DB_PATH.parent/'backups').glob('pre_v1_1_*.sqlite3'))
    legacy=tmp_path/'legacy.sqlite3';shutil.copy2(snapshot,legacy)
    with sqlite3.connect(legacy) as conn:
        conn.execute("INSERT INTO garments(id,name,category,compartment_id,photo_filename) VALUES(77,'Legacy shirt','shirt',4,'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg')")
        conn.execute('INSERT INTO movements(garment_id,to_compartment_id) VALUES(77,4)')
    photo=store.UPLOADS_PATH/'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg';photo.write_bytes(b'preserved-photo')
    monkeypatch.setattr(store,'DB_PATH',legacy)
    store.init_db();store.init_db()
    with store.db() as conn:
        row=conn.execute('SELECT * FROM garments WHERE id=77').fetchone()
        assert row['compartment_id']==4
        assert conn.execute('SELECT COUNT(*) FROM movements').fetchone()[0]==1
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    assert photo.read_bytes()==b'preserved-photo'
    assert len(plan(client)['compartments'])==9
