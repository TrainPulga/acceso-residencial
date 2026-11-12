"""PAD: contrato real del modelo y flujos simulados; no precisión en personas."""
import hashlib
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from access_app.pad import PadEngine, PadSequence
from access_app.backups import create_backup, import_data
from access_app.store import Store
from test_api import client, enroll, scan, image


def test_original_onnx_preprocessing_uses_rgb_and_per_channel_normalization():
    frame=np.zeros((100,100,3),np.uint8);frame[:]=[10,20,30]  # BGR
    tensor=PadEngine.prepare(frame,[{'x':0,'y':0,'w':100,'h':100}])
    assert tensor.shape==(1,3,128,128) and tensor.dtype==np.float32
    assert tensor[0,:,0,0]==pytest.approx((np.array([30,20,10])-[151.2405,119.5950,107.8395])/[63.0105,56.4570,55.0035])


def test_authentic_pad_model_loads_and_executes_without_claiming_human_accuracy():
    engine=PadEngine(Path(__file__).resolve().parents[1]/'models'/'pad')
    rng=np.random.default_rng(42)
    frame=rng.integers(0,256,(160,160,3),dtype=np.uint8)
    score=engine.predict(frame,[{'x':20,'y':20,'w':120,'h':120}])
    assert 0<=score<=1
    # Un score de ruido NO es un ejemplo bona fide ni un ataque real etiquetado.


@pytest.mark.parametrize('boxes',[[],[{'x':-1,'y':0,'w':100,'h':100}],
    [{'x':0,'y':0,'w':50,'h':50}], [{'x':0,'y':0,'w':100,'h':100}]*2])
def test_pad_rejects_ambiguous_small_or_clipped_regions(boxes):
    with pytest.raises(ValueError): PadEngine.prepare(np.zeros((100,100,3),np.uint8),boxes)


def test_pad_model_hash_mismatch_fails_closed(tmp_path):
    import json
    (tmp_path/'anti-spoof-mn3.onnx').write_bytes(b'broken')
    (tmp_path/'manifest.json').write_text(json.dumps({'file':'anti-spoof-mn3.onnx','sha256':'wrong'}))
    with pytest.raises(RuntimeError): PadEngine(tmp_path)


def test_sequence_requires_distinct_recent_spaced_captures_of_same_identity():
    now=[0.0];gate=PadSequence(clock=lambda:now[0]);key=('session','camera')
    assert not gate.observe(key,'r1','a',.99)['passed']
    now[0]=1.1;assert not gate.observe(key,'r1','b',.99)['passed']
    now[0]=2.2;assert gate.observe(key,'r1','c',.99)['passed']
    now[0]=3.3;assert not gate.observe(key,'r2','d',.99)['passed']
    now[0]=4.4;assert not gate.observe(key,'r2','d',.99)['passed']
    now[0]=20;assert gate.observe(key,'r2','e',.99)['samples']==1


def test_temporal_sequence_is_separate_by_session_and_camera_and_resets_on_uncertainty():
    now=[0.0];gate=PadSequence(clock=lambda:now[0])
    gate.observe(('s','c'),'r','a',.99)
    now[0]=1.1;assert gate.observe(('other','c'),'r','b',.99)['samples']==1
    assert gate.observe(('s','other-camera'),'r','c',.99)['samples']==1
    result=gate.observe(('s','c'),'r','d',.50)
    assert result['state']=='incierto' and not result['passed'] and result['samples']==0
    assert gate.observe(('s','c'),'r','e',.01)['state']=='posible_presentacion'
    assert gate.observe(('s','c'),'r','f',float('nan'))['state']=='error'


def test_frame_that_fails_pad_cannot_identify_or_issue_pass_despite_matching_face(client):
    enroll(client);client.app.state.pad.score=.01
    result=scan(client)
    assert result['face_match_found'] and not result['recognized'] and result['resident'] is None
    assert result['pad']['state']=='posible_presentacion' and 'pass_token' not in result
    assert client.get('/api/events').json()==[]


def test_inconclusive_pad_is_not_a_spoof_accusation_and_does_not_issue_pass(client):
    enroll(client);client.app.state.pad.score=.70
    result=scan(client)
    assert result['pad']['state']=='incierto' and 'pass_token' not in result
    assert not result['recognized']


def test_bad_next_frame_revokes_previously_issued_pass_and_pin_cannot_bypass(client):
    enroll(client);old=scan(client)['pass_token']
    client.app.state.pad.score=.01;scan(client)
    result=client.post('/api/passages',json={'token':old,'camera_id':'browser-access','direction':'entrada',
        'crossing_observed':True,'resident_pin':'729481','pad':{'passed':True}})
    assert result.status_code==409 and client.get('/api/events').json()==[]


def test_detector_only_mode_revokes_access_evidence(client):
    enroll(client);old=scan(client)['pass_token']
    assert client.post('/api/analyze?mode=detect',json={'image':image((211,0,0))}).status_code==200
    assert client.post('/api/passages',json={'token':old,'camera_id':'browser-access','direction':'entrada',
        'crossing_observed':True}).status_code==409


def test_stop_reset_discards_sequence_and_pass(client):
    enroll(client);old=scan(client)['pass_token']
    assert client.post('/api/access/reset',json={'camera_id':'browser-access'}).status_code==200
    assert client.post('/api/passages',json={'token':old,'camera_id':'browser-access','direction':'salida',
        'crossing_observed':True}).status_code==409


def test_missing_or_failed_pad_never_falls_back_to_face_only(client):
    enroll(client)
    client.app.state.pad=None;client.app.state.pad_error='PAD de prueba ausente'
    result=scan(client)
    assert result['pad']['state']=='no_disponible' and 'pass_token' not in result
    assert enroll(client).status_code==503


def test_enrollment_rejects_failed_pad_before_storing_template(client):
    client.app.state.pad.score=.01
    assert enroll(client).status_code==400
    assert client.app.state.store.residents()==[]


def test_server_camera_uses_same_pad_gate_without_browser_uploaded_image(client,monkeypatch):
    enroll(client)
    record=client.post('/api/cameras',json={'label':'Acceso de prueba','role':'access','source':'usb:1',
        'authorized_private_use':True}).json()
    count=[0]
    def frame(camera_id):
        count[0]+=1
        from access_app.vision import decode_image
        return decode_image(image((205+count[0],1,0)))
    monkeypatch.setattr(client.app.state.hub,'frame',frame)
    for n in range(3):
        response=client.post('/api/cameras/'+record['id']+'/analyze').json()
        assert response['recognized']==(n==2)
    assert response['pad']['passed'] and response['pass_token']
    assert client.post('/api/analyze',json={'camera_id':record['id'],'image':image((230,1,0))}).status_code==400
    token=response['pass_token']
    assert client.post('/api/cameras/'+record['id']+'/disconnect').status_code==200
    assert client.post('/api/passages',json={'token':token,'camera_id':record['id'],'direction':'entrada',
        'crossing_observed':True}).status_code==409


def pad_trial(client,color,presentation='persona_real',**changes):
    body={'image':image(color),'subject_code':'V01','session':'pad_dia2','phase':'prueba','condition':'frontal',
        'presentation':presentation,'consent':True,'independent_capture':True}
    body.update(changes)
    return client.post('/api/evaluation/pad/trials',json=body)


def test_pad_measurement_reports_real_denominators_and_no_invented_rates(client,monkeypatch):
    empty=client.get('/api/evaluation/pad/report').json()
    assert empty['total_trials']==0 and empty['sessions']==[]
    assert pad_trial(client,(190,0,0)).status_code==201
    client.app.state.pad.score=.01
    assert pad_trial(client,(191,0,0)).status_code==201
    assert pad_trial(client,(192,0,0),'foto_impresa').status_code==201
    client.app.state.pad.score=.99
    assert pad_trial(client,(193,0,0),'foto_pantalla').status_code==201
    original=client.app.state.pad.predict
    def unsuitable(*args): raise ValueError('Captura no apta simulada')
    monkeypatch.setattr(client.app.state.pad,'predict',unsuitable)
    assert pad_trial(client,(194,0,0)).status_code==201
    monkeypatch.setattr(client.app.state.pad,'predict',original)
    report=client.get('/api/evaluation/pad/report').json();session=report['sessions'][0]
    assert session['attack_accepted_operational']=={'count':1,'total':2,'rate':.5}
    assert session['real_rejected_operational']=={'count':2,'total':3,'rate':2/3}
    assert session['real_rejected_evaluable_captures']=={'count':1,'total':2,'rate':.5}
    assert session['attack_accepted_evaluable_captures']=={'count':1,'total':2,'rate':.5}
    assert session['unsuitable_captures']==1
    assert session['attack_accepted_by_type']['video_pantalla']['rate'] is None
    assert report['validated_locally'] is False and 'NO mide' in report['unit']
    assert client.get('/api/events').json()==[]
    assert 'image' not in report['rows'][0]
    assert b'pad_dia2' not in (client.app.state.store.directory/'access.sqlite3').read_bytes()
    assert pad_trial(client,(193,0,0),'foto_pantalla').status_code==400
    assert pad_trial(client,(194,0,0),phase='exploracion').status_code==400
    assert client.delete('/api/evaluation/pad/trials').status_code==200
    assert client.get('/api/evaluation/pad/report').json()['total_trials']==0


def test_security_role_cannot_add_or_read_academic_pad_trials(client):
    from test_accounts_and_restrictions import security,headers
    session,_=security(client)
    assert client.get('/api/evaluation/pad/report',headers=headers(session['token'])).status_code==403
    assert client.post('/api/evaluation/pad/trials',json={},headers=headers(session['token'])).status_code==403


def test_pad_trial_without_authorization_or_with_invalid_label_is_rejected(client):
    assert pad_trial(client,(195,0,0),consent=False).status_code==400
    assert pad_trial(client,(196,0,0),presentation='invented').status_code==422


def test_pad_trials_survive_backup_and_restore(client,tmp_path):
    pad_trial(client,(197,0,0))
    store=client.app.state.store;backup=create_backup(store.directory,tmp_path/'copies')
    imported=import_data(backup,tmp_path/'restored');restored=Store(imported)
    from access_app.pad_trials import PadTrials
    assert PadTrials(restored).report()['total_trials']==1
    restored.db.close()
