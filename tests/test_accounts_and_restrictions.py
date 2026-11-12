"""tests/test_accounts_and_restrictions.py — permisos, revocación y restricciones con datos sintéticos."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from access_app.auth import AuthError, password_hash, verify_password
from access_app.backups import create_backup, import_data
from access_app.store import Store
from test_api import client, enroll, scan
from test_visits import payload, move

PASSWORD = "ClaveDePrueba123!"
NEXT = "OtraClaveDePrueba123!"


def headers(token):
    return {"Authorization": "Bearer "+token}


def security(client, username="seguridad1"):
    user = client.post('/api/users', json={"name": "Operador de prueba", "username": username,
        "password": PASSWORD, "role": "seguridad"})
    assert user.status_code == 201, user.text
    first = client.post('/api/auth/login', json={"username": username, "password": PASSWORD}).json()
    assert client.post('/api/auth/password', json={"current_password": PASSWORD, "password": NEXT},
                       headers=headers(first["token"])).status_code == 200
    result = client.post('/api/auth/login', json={"username": username, "password": NEXT})
    assert result.status_code == 200, result.text
    return result.json(), user.json()


def restriction(client, resident_id=None, **changes):
    now = datetime.now(timezone.utc)
    body = {"resident_id": resident_id, "name": "Persona externa de prueba", "reference": "REF-LAB-01",
            "reason": "Decisión administrativa de laboratorio", "valid_from": (now-timedelta(minutes=1)).isoformat(),
            "valid_until": (now+timedelta(hours=2)).isoformat(), "authorized_decision": True, "identity_verified": True}
    body.update(changes)
    response = client.post('/api/restrictions', json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_passwords_are_salted_slow_hashes_not_reversible_text():
    a, b = password_hash(PASSWORD), password_hash(PASSWORD)
    assert a != b and PASSWORD not in a
    assert verify_password(PASSWORD, a) and not verify_password(NEXT, a)
    assert not verify_password(PASSWORD, 'broken')


def test_setup_key_stops_being_a_login_or_user_creation_backdoor(client):
    key = client.app.state.store.admin_token
    assert client.get('/api/status', headers=headers(key)).status_code == 401
    result = client.post('/api/auth/setup', json={"setup_key": key, "name": "Otra cuenta", "username": "otroadmin",
        "password": PASSWORD})
    assert result.status_code == 409


def test_security_role_cannot_manage_accounts_models_or_restrictions(client):
    session, _ = security(client)
    h = headers(session['token'])
    assert client.get('/api/status', headers=h).status_code == 200
    assert client.get('/api/residents', headers=h).status_code == 200
    assert client.get('/api/restrictions', headers=h).status_code == 200
    for path in ['/api/users','/api/audit','/api/evaluation/report']:
        assert client.get(path, headers=h).status_code == 403
    assert client.post('/api/residents', json={"name":"Prueba","unit":"1","building":"LAB","consent":True,
        "adult_volunteer":True,"images":["abcd1234"]*3}, headers=h).status_code == 403
    assert client.post('/api/cameras', json={"label":"Prueba","role":"access","source":"usb:0",
        "authorized_private_use":True}, headers=h).status_code == 403


def test_new_operator_must_change_password_and_old_session_is_revoked(client):
    client.post('/api/users', json={"name":"Prueba","username":"operador2","password":PASSWORD,"role":"seguridad"})
    first = client.post('/api/auth/login', json={"username":"operador2","password":PASSWORD}).json()
    assert first['user']['force_change']
    assert client.get('/api/status', headers=headers(first['token'])).status_code == 403
    assert client.post('/api/auth/password', json={"current_password":PASSWORD,"password":NEXT},
                       headers=headers(first['token'])).status_code == 200
    assert client.get('/api/status', headers=headers(first['token'])).status_code == 401


def test_disabling_or_changing_role_revokes_sessions(client):
    session, user = security(client)
    assert client.patch('/api/users/'+user['id'], json={"role":"seguridad","active":False}).status_code == 200
    assert client.get('/api/status', headers=headers(session['token'])).status_code == 401
    assert client.post('/api/auth/login', json={"username":user['username'],"password":NEXT}).status_code == 401


def test_admin_cannot_disable_self_and_logout_expires_session(client):
    me = client.get('/api/auth/me').json()
    assert client.patch('/api/users/'+me['id'], json={"role":"seguridad","active":False}).status_code == 400
    token = client.headers['Authorization']
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/status', headers={"Authorization":token}).status_code == 401


def test_login_attempts_lock_out_and_sessions_expire(client):
    for _ in range(5):
        assert client.post('/api/auth/login', json={"username":"adminprueba","password":"wrong"}).status_code == 401
    assert client.post('/api/auth/login', json={"username":"adminprueba","password":PASSWORD}).status_code == 429
    clock = client.app.state.accounts.clock()
    client.app.state.accounts.clock = lambda: clock+301
    session = client.post('/api/auth/login', json={"username":"adminprueba","password":PASSWORD}).json()
    client.app.state.accounts.clock = lambda: clock+9*3600
    assert client.get('/api/status', headers=headers(session['token'])).status_code == 401


def test_active_restriction_blocks_entry_even_if_created_after_matching_but_allows_exit(client):
    resident = enroll(client).json()
    match = scan(client)
    record = restriction(client, resident['id'])
    response = scan(client)
    assert response['recognized'] and not response['entry_allowed'] and response['restriction_active']
    body={"token":match['pass_token'],"camera_id":"browser-access","direction":"entrada","crossing_observed":True,"resident_pin":"729481"}
    assert client.post('/api/passages', json=body).status_code == 409
    body.update(token=scan(client)['pass_token'],direction='salida')
    assert client.post('/api/passages', json=body).status_code == 201
    assert client.post('/api/restrictions/'+record['id']+'/release', json={"reason":"Revisión de laboratorio"}).status_code == 200
    assert scan(client)['entry_allowed']


def test_a_match_token_cannot_be_used_by_another_operator(client):
    enroll(client)
    matched = scan(client)
    session, _ = security(client)
    assert client.post('/api/passages', json={"token":matched['pass_token'],"camera_id":"browser-access",
        "direction":"entrada","crossing_observed":True,"resident_pin":"729481"}, headers=headers(session['token'])).status_code == 409


def test_external_restrictions_require_verified_identity_and_are_not_facial_profiles(client):
    now = datetime.now(timezone.utc)
    bad={"name":"Prueba","reference":"REF","reason":"Prueba administrativa","valid_from":now.isoformat(),
         "valid_until":(now+timedelta(hours=1)).isoformat(),"authorized_decision":True,"identity_verified":False}
    assert client.post('/api/restrictions', json=bad).status_code == 400
    record = restriction(client)
    assert record['type']=='externo_manual' and record['resident_id'] is None
    assert client.app.state.store.gallery()==[]
    session, _ = security(client)
    listed=client.get('/api/restrictions', headers=headers(session['token'])).json()['items'][0]
    assert 'reason' not in listed
    assert client.post('/api/restrictions/'+record['id']+'/release', json={"reason":"Prueba"},
                       headers=headers(session['token'])).status_code == 403


def test_linked_external_restriction_blocks_visit_entry_without_blocking_exit(client):
    host = enroll(client).json()
    record = restriction(client)
    created=client.post('/api/visits', json=payload(host,external_record_id=record['id'],external_identity_verified=True)).json()
    assert move(client, created, 'entry').status_code == 409
    client.post('/api/restrictions/'+record['id']+'/release', json={"reason":"Revisión documentada"})
    assert move(client, created, 'entry').status_code == 200
    assert move(client, created, 'exit').status_code == 200


def test_audit_identifies_operator_excludes_password_and_continuous_scans(client):
    resident = enroll(client).json()
    before=client.app.state.audit.verify()['checked']
    scan(client);scan(client)
    assert client.app.state.audit.verify()['checked']==before
    report=client.get('/api/audit').json()
    assert report['integrity']['valid']
    assert report['items'][0]['operator']['username']=='adminprueba'
    binary=(client.app.state.store.directory/'access.sqlite3').read_bytes()
    assert PASSWORD.encode() not in binary
    assert b'Administrador de laboratorio' not in binary


def test_tampering_or_truncating_audit_is_detected(client):
    audit=client.app.state.audit;store=client.app.state.store
    enroll(client)
    assert audit.verify()['valid']
    last=store.db.execute('SELECT max(id) FROM audit_log').fetchone()[0]
    store.db.execute('DELETE FROM audit_log WHERE id=?',(last,));store.db.commit()
    assert not audit.verify()['valid']


def test_audit_failure_is_visible_and_blocks_further_changes(client):
    with patch.object(client.app.state.audit,'append',side_effect=OSError('simulated full disk')):
        response=enroll(client, configure_pin=False)
    assert response.status_code==201 and response.headers['X-Audit-Status']=='failed'
    assert client.get('/api/status').json()['audit_error']
    assert client.post('/api/evaluation/trials',json={"image":"abcdefgh","subject_code":"V01","session":"TEST",
        "phase":"prueba","condition":"frontal","consent":True,"independent_capture":True}).status_code==503
    assert client.get('/api/audit').json()['incident'] is not None
    assert client.post('/api/audit/reconcile',json={'reason':'Revisión de la operación sintética y su registro'}).status_code==200
    assert not client.get('/api/status').json()['audit_error']
    assert client.get('/api/audit').json()['incident'] is None


def test_restore_keeps_users_and_data_but_does_not_reactivate_old_sessions(client,tmp_path):
    token=client.headers['Authorization'].removeprefix('Bearer ')
    backup=create_backup(client.app.state.store.directory,tmp_path/'copies')
    destination=import_data(backup,tmp_path/'restored')
    restored=Store(destination)
    from access_app.auth import Accounts
    accounts=Accounts(restored)
    assert accounts.users()[0]['username']=='adminprueba'
    with pytest.raises(AuthError):accounts.resolve(token)
    session=accounts.login('adminprueba',PASSWORD,'local')
    assert accounts.resolve(session['token'])['role']=='admin'
    restored.db.close()


def test_security_visit_history_and_audit_use_the_authenticated_operator(client):
    host=enroll(client).json()
    session,user=security(client)
    created=client.post('/api/visits',json=payload(host),headers=headers(session['token'])).json()
    old=client.headers['Authorization']
    client.headers['Authorization']='Bearer '+session['token']
    try:
        assert move(client,created,'entry').status_code==200
        detail=client.get('/api/visits/'+str(created['id'])).json()
        assert all(e['authenticated_operator']==user['id'] for e in detail['history'])
    finally:client.headers['Authorization']=old
    rows=client.get('/api/audit').json()['items']
    assert rows[0]['operator']['id']==user['id']


def test_admin_password_reset_revokes_session_and_requires_new_password(client):
    session,user=security(client)
    assert client.post('/api/users/'+user['id']+'/password',json={'password':PASSWORD}).status_code==200
    assert client.get('/api/status',headers=headers(session['token'])).status_code==401
    reset=client.post('/api/auth/login',json={'username':user['username'],'password':PASSWORD}).json()
    assert reset['user']['force_change']


def test_future_restriction_does_not_block_current_entry(client):
    resident=enroll(client).json();now=datetime.now(timezone.utc)
    restriction(client,resident['id'],valid_from=(now+timedelta(hours=1)).isoformat(),
                valid_until=(now+timedelta(hours=2)).isoformat())
    assert scan(client)['entry_allowed']


def test_audit_retention_preserves_chain_anchor(tmp_path):
    from access_app.audit import Audit
    store=Store(tmp_path/'audit-test');audit=Audit(store)
    user={'id':'technical-test','username':'test','name':'Prueba','role':'admin'}
    with patch('access_app.audit.utcnow',return_value='2026-01-01T00:00:00.000+00:00'):
        audit.append(user,'OLD')
    with patch('access_app.audit.utcnow',return_value='2026-10-17T00:00:00.000+00:00'):
        audit.append(user,'NEW')
    audit.prune('2026-02-01T00:00:00.000+00:00')
    assert audit.verify()=={'valid':True,'checked':1,'error':None}
    audit.prune('2027-01-01T00:00:00.000+00:00')
    assert audit.verify()['valid'] and not audit.rows()
    store.db.close()


def test_report_requires_admin_and_does_not_invent_accuracy(client):
    response=client.get('/api/evaluation/report.html')
    assert response.status_code==200 and 'No hay ensayos aportados' in response.text
    session,_=security(client)
    assert client.get('/api/evaluation/report.html',headers=headers(session['token'])).status_code==403
