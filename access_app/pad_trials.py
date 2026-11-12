"""Ensayos PAD de una captura, etiquetados por humano y cifrados; sin fotos."""
import hashlib
import json
import math
import re
import time

from access_app.pad import REAL_THRESHOLD
from access_app.store import utcnow


class PadTrials:
    def __init__(self, store):
        self.store=store

    def rows(self):
        with self.store.lock:
            return [self.store.open(r[0]) for r in self.store.db.execute('SELECT record FROM pad_trials ORDER BY id')]

    def record(self, payload, image, vision, pad, source):
        if not payload.consent or not payload.independent_capture:
            raise ValueError('Confirmá autorización adulta y captura independiente, con etiqueta conocida')
        if not all(re.fullmatch(r'[A-Za-z0-9_-]{2,40}',v) for v in (payload.subject_code,payload.session)):
            raise ValueError('Usá códigos sin nombres, de 2–40 letras, números, guiones o guion bajo')
        fingerprint=hashlib.sha256(image.tobytes()).hexdigest()
        config={**pad.metadata,'required_sequence_samples':3,'source':source,'unit':'single_capture_not_access_sequence'}
        config_id=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
        with self.store.lock:
            old=self.rows()
            if any(r['frame_sha256']==fingerprint for r in old):
                raise ValueError('Esta captura ya se midió; tomá una nueva')
            if any(r['session']==payload.session and (r['configuration_id']!=config_id or r['phase']!=payload.phase) for r in old):
                raise ValueError('Cambió modelo/configuración/fase: usá una sesión nueva')
            started=time.perf_counter()
            score=None
            try:
                boxes=vision.boxes(vision.detect(image))
                score=pad.predict(image,boxes)
                if not math.isfinite(score) or not 0<=score<=1:
                    raise ValueError('Salida PAD inválida')
                suitable=True
            except ValueError:
                score=None
                suitable=False
            accepted=bool(suitable and score>=REAL_THRESHOLD)
            row={'occurred_at':utcnow(),'subject_code':payload.subject_code,'session':payload.session,
                 'phase':payload.phase,'presentation':payload.presentation,'source':source,
                 'condition':payload.condition,'bona_fide_score':score,'pad_capture_accepted':accepted,
                 'capture_suitable':suitable,'latency_ms':(time.perf_counter()-started)*1000,
                 'frame_sha256':fingerprint,'configuration':config,'configuration_id':config_id,
                 'label_is_operator_supplied':True,'consent_declared':True}
            self.store.db.execute('INSERT INTO pad_trials(record) VALUES (?)',(self.store.seal(row),))
            self.store.db.commit()
            return row

    def clear(self):
        with self.store.lock,self.store.db:
            self.store.db.execute('DELETE FROM pad_trials')

    def report(self):
        rows=self.rows()
        groups=[]
        for session in sorted({r['session'] for r in rows}):
            subset=[r for r in rows if r['session']==session]
            real=[r for r in subset if r['presentation']=='persona_real']
            attacks=[r for r in subset if r['presentation']!='persona_real']
            def rate(count,total):return {'count':count,'total':total,'rate':count/total if total else None}
            by_attack={kind:rate(sum(r['pad_capture_accepted'] for r in attacks if r['presentation']==kind),
                                sum(r['presentation']==kind for r in attacks))
                       for kind in ('foto_impresa','foto_pantalla','video_pantalla')}
            evaluable_attacks=[r for r in attacks if r['capture_suitable']]
            evaluable_real=[r for r in real if r['capture_suitable']]
            groups.append({'session':session,'phase':subset[0]['phase'],'trials':len(subset),
                'participants':len({r['subject_code'] for r in subset}),'configuration':subset[0]['configuration'],
                'attack_accepted_operational':rate(sum(r['pad_capture_accepted'] for r in attacks),len(attacks)),
                'real_rejected_operational':rate(sum(not r['pad_capture_accepted'] for r in real),len(real)),
                'unsuitable_captures':sum(not r['capture_suitable'] for r in subset),
                'attack_accepted_evaluable_captures':rate(sum(r['pad_capture_accepted'] for r in evaluable_attacks),len(evaluable_attacks)),
                'real_rejected_evaluable_captures':rate(sum(not r['pad_capture_accepted'] for r in evaluable_real),len(evaluable_real)),
                'attack_accepted_by_type':by_attack})
        return {'total_trials':len(rows),'sessions':groups,'rows':rows,'validated_locally':False,
                'unit':'Una captura; NO mide la decisión temporal completa de acceso',
                'warning':'Etiquetas humanas y sesiones independientes requieren supervisión. Tasas operativas incluyen capturas no aptas; no se presentan como certificación ISO ni como precisión poblacional.'}
