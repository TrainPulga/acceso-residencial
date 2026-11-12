"""Regresiones de ataques locales simulados; no certificación ni prueba de PAD."""
import asyncio
import base64
import io
import os
import stat
import time

import pytest
from PIL import Image

from access_app.auth import AuthError, IDLE_SECONDS
from access_app.cameras import validate_source
from access_app.file_security import private_path
from access_app.security import BoundedBody, SecurityHeaders
from access_app.store import Store
from access_app.vision import decode_image
from test_api import client, enroll, scan
from test_accounts_and_restrictions import security, headers, PASSWORD


def enter(client, pin='', direction='entrada', token=None, auth=None):
    return client.post('/api/passages', json={
        'token': token or scan(client)['pass_token'], 'camera_id':'browser-access',
        'direction': direction, 'crossing_observed': True, 'resident_pin': pin},
        **({'headers': auth} if auth else {}))


def test_single_image_does_not_complete_pad_sequence(client):
    from test_api import image
    enroll(client)
    first=client.post('/api/analyze',json={'image':image((201,1,0))}).json()
    assert first['face_match_found'] and not first['recognized'] and 'pass_token' not in first
    assert first['pad']['samples']==1
    assert enter(client).status_code==201  # el helper reúne la secuencia PAD simulada


def test_previous_pin_is_not_required_when_face_and_pad_pass(client):
    enroll(client)
    with client.app.state.store.db:
        client.app.state.store.db.execute('DELETE FROM resident_credentials')
    result=scan(client)
    assert result['recognized'] and result['entry_allowed'] and not result['entry_pin_required']
    assert enter(client).status_code==201
    assert enter(client,direction='salida').status_code==201


def test_legacy_pin_lockout_does_not_control_face_pad_access(client):
    from access_app.credentials import PinError
    resident=enroll(client).json()
    manager=client.app.state.credentials
    for _ in range(5):
        with pytest.raises(PinError): manager.verify(resident['id'],'918362')
    with pytest.raises(PinError) as error: manager.verify(resident['id'],'729481')
    assert error.value.status==429
    assert enter(client).status_code==201


def test_pin_change_requires_admin_and_identity_confirmation_and_never_discloses_secret(client):
    resident=enroll(client).json()
    session,_=security(client)
    path='/api/residents/'+resident['id']+'/pin'
    assert client.post(path,json={'pin':'837192','identity_verified':True},headers=headers(session['token'])).status_code == 403
    assert client.post(path,json={'pin':'837192'}).status_code == 400
    assert client.post(path,json={'pin':'111111','identity_verified':True}).status_code == 400
    assert client.post(path,json={'pin':'837192','identity_verified':True}).status_code == 200
    assert enter(client).status_code == 201
    assert '837192' not in client.get('/api/residents').text
    assert b'837192' not in (client.app.state.store.directory/'access.sqlite3').read_bytes()
    assert '837192' not in client.get('/api/audit').text
    assert client.delete('/api/residents/'+resident['id']).status_code == 200
    assert client.app.state.store.db.execute('SELECT count(*) FROM resident_credentials').fetchone()[0] == 0


def test_match_is_bound_to_login_session_even_for_same_operator(client):
    enroll(client)
    token=scan(client)['pass_token']
    login=client.post('/api/auth/login',json={'username':'adminprueba','password':PASSWORD}).json()
    assert enter(client,'729481',token=token,auth=headers(login['token'])).status_code == 409


def test_session_expires_after_idle_time_and_absolute_lifetime(client):
    accounts=client.app.state.accounts
    initial=time.time()
    accounts.clock=lambda:initial+IDLE_SECONDS-1
    assert client.get('/api/status').status_code == 200
    accounts.clock=lambda:initial+2*IDLE_SECONDS-2
    assert client.get('/api/status').status_code == 200
    accounts.clock=lambda:initial+3*IDLE_SECONDS
    assert client.get('/api/status').status_code == 401
    accounts.clock=lambda:initial
    login=accounts.login('adminprueba',PASSWORD,'test')
    with accounts.store.db:
        accounts.store.db.execute('UPDATE sessions SET last_seen_at=?',(initial+8*3600,))
    accounts.clock=lambda:initial+8*3600+1
    with pytest.raises(AuthError):
        accounts.resolve(login['token'])


def test_account_lockout_cannot_be_bypassed_by_rotating_source(client):
    accounts=client.app.state.accounts
    for n in range(5):
        with pytest.raises(AuthError) as error:
            accounts.login('adminprueba','wrong','source-'+str(n))
        assert error.value.status == 401
    with pytest.raises(AuthError) as error:
        accounts.login('adminprueba',PASSWORD,'new-source')
    assert error.value.status == 429


def test_login_session_count_is_bounded_per_user(client):
    accounts=client.app.state.accounts
    tokens=[accounts.login('adminprueba',PASSWORD,'test')['token'] for _ in range(4)]
    assert accounts.store.db.execute('SELECT count(*) FROM sessions').fetchone()[0] == 3
    with pytest.raises(AuthError): accounts.resolve(tokens[0])
    assert accounts.resolve(tokens[-1])['role'] == 'admin'


def test_wrong_unicode_setup_key_is_controlled_not_server_error(tmp_path):
    from access_app.main import create_app
    from fastapi.testclient import TestClient
    from test_api import FakeVision
    with TestClient(create_app(tmp_path,FakeVision()), base_url="http://127.0.0.1") as c:
        result=c.post('/api/auth/setup',json={'setup_key':'á'*32,'name':'Prueba','username':'adminprueba','password':PASSWORD})
        assert result.status_code == 401


@pytest.mark.parametrize('length', [None, b'1'])
def test_body_limit_counts_chunks_before_application_even_without_honest_length(length):
    called=[];messages=[]
    async def application(scope,receive,send): called.append(True)
    app=SecurityHeaders(BoundedBody(application,limit=10))
    chunks=iter([{'type':'http.request','body':b'123456','more_body':True},
                 {'type':'http.request','body':b'123456','more_body':False}])
    async def receive(): return next(chunks)
    async def send(message): messages.append(message)
    scope={'type':'http','headers':[] if length is None else [(b'content-length',length)]}
    asyncio.run(app(scope,receive,send))
    assert not called and messages[0]['status'] == 413
    assert dict(messages[0]['headers'])[b'x-frame-options'] == b'DENY'


def test_errors_have_security_headers_and_do_not_echo_secrets(client):
    secret='PRIVATE-PIN-IN-INVALID-INPUT'
    resident=enroll(client).json()
    result=client.post('/api/residents/'+resident['id']+'/pin',json={'pin':secret,'identity_verified':True})
    assert result.status_code == 422 and secret not in result.text
    for response in [result, client.get('/api/status',headers={'Origin':'https://outside.example'})]:
        assert response.headers['cache-control'] == 'no-store'
        assert "base-uri 'none'" in response.headers['content-security-policy']
        assert response.headers['x-frame-options'] == 'DENY'


@pytest.mark.parametrize('source', ['rtsp://127.0.0.1/feed','rtsp://[::1]/feed',
    'http://192.168.1.2/video','https://10.0.0.2/playlist.m3u8',
    'rtsp://192.168.1.2:99999/video','rtsp://192.168.1.2/video\r\nGET /',
    'rtsp://192.168.1.2/video#hidden','usb:999999'])
def test_camera_local_service_and_nested_http_sources_are_rejected(source):
    with pytest.raises(ValueError): validate_source(source)


def test_non_jpeg_png_is_rejected_before_opencv_decode():
    data=io.BytesIO();Image.new('RGB',(100,100),'white').save(data,'GIF')
    with pytest.raises(ValueError): decode_image(base64.b64encode(data.getvalue()).decode())


def test_data_and_backup_permissions_are_private(tmp_path):
    from access_app.backups import create_backup
    store=Store(tmp_path/'data')
    backup=create_backup(store.directory)
    for folder in [store.directory,backup]:
        private_path(folder)  # En Windows ejecuta la API real si se corre allí.
        if os.name != 'nt':
            assert stat.S_IMODE(folder.stat().st_mode) == 0o700
            for name in ['access.sqlite3','local.key','admin.token']:
                assert stat.S_IMODE((folder/name).stat().st_mode) == 0o600
    store.db.close()


@pytest.mark.skipif(os.name == 'nt', reason='En Windows crear enlaces depende de permisos del SO')
def test_secret_symlink_is_rejected_without_changing_target(tmp_path):
    target=tmp_path/'untouched';target.write_text('do not overwrite')
    directory=tmp_path/'data';directory.mkdir();(directory/'local.key').symlink_to(target)
    with pytest.raises(RuntimeError,match='enlaces'): Store(directory)
    assert target.read_text() == 'do not overwrite'


def test_schema4_upgrade_revokes_sessions_but_preserves_accounts_and_face_templates(tmp_path):
    from access_app.auth import Accounts
    store=Store(tmp_path/'data',model_signature='original-sface')
    accounts=Accounts(store)
    old=accounts.setup(store.admin_token,'adminprueba','Prueba',PASSWORD)
    resident=store.add_resident({'name':'Participante de prueba'},[1,0])
    encrypted=store.db.execute('SELECT template FROM residents').fetchone()[0]
    store.db.execute('DROP TABLE pad_trials')
    store.db.execute('DROP TABLE resident_credentials')
    store.db.execute('ALTER TABLE sessions DROP COLUMN last_seen_at')
    store.db.execute('PRAGMA user_version=4');store.db.commit();store.db.close()
    upgraded=Store(store.directory,model_signature='original-sface')
    assert upgraded.migration_backup is not None
    assert upgraded.db.execute('PRAGMA user_version').fetchone()[0] == 6
    assert upgraded.db.execute('SELECT template FROM residents').fetchone()[0] == encrypted
    assert upgraded.resident(resident)
    restored=Accounts(upgraded)
    with pytest.raises(AuthError): restored.resolve(old['token'])
    assert restored.login('adminprueba',PASSWORD,'test')['user']['id'] == old['user']['id']
    upgraded.db.close()


def test_old_http_camera_fails_with_controlled_error_without_opening_stream(client):
    store=client.app.state.store
    camera_id=store.add_camera('Fuente de versión previa','access','http://192.168.1.2/legacy-video')
    response=client.post('/api/cameras/'+camera_id+'/connect')
    assert response.status_code == 400
    assert not client.app.state.hub.streams


def test_service_restart_revokes_existing_sessions_without_deleting_accounts(tmp_path):
    from access_app.auth import Accounts
    from access_app.main import create_app
    from test_api import FakeVision
    # La firma debe coincidir con el motor inyectado, como en el mismo servicio.
    app=create_app(tmp_path,FakeVision())
    old=app.state.accounts.setup(app.state.store.admin_token,'adminprueba','Prueba',PASSWORD)
    app.state.store.db.close()
    again=create_app(tmp_path,FakeVision())
    with pytest.raises(AuthError): again.state.accounts.resolve(old['token'])
    assert again.state.accounts.login('adminprueba',PASSWORD,'test')['user']['id'] == old['user']['id']
    again.state.store.db.close()
