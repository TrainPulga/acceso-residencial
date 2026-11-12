/* tests/frontend_smoke.cjs — DOM simulado; no renderer, webcam ni resultados biométricos reales. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const root=path.join(__dirname,'../access_app/static');
const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8123',runScripts:'dangerously'});
const w=dom.window,doc=w.document;
w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
w.HTMLDialogElement.prototype.close=function(){this.open=false;};
w.HTMLCanvasElement.prototype.getContext=()=>({clearRect(){},strokeRect(){},drawImage(){}});
w.HTMLCanvasElement.prototype.toDataURL=()=> 'data:image/jpeg;base64,dGVzdA==';
w.HTMLMediaElement.prototype.play=async()=>{};
Object.defineProperty(w.HTMLVideoElement.prototype,'videoWidth',{get:()=>640});
Object.defineProperty(w.HTMLVideoElement.prototype,'videoHeight',{get:()=>480});
w.confirm=()=>true;
let stops=0,setup=true;
let downloads=0,recorders=0;
w.URL.createObjectURL=()=> 'blob:simulated-test';w.URL.revokeObjectURL=()=>{};
w.HTMLAnchorElement.prototype.click=function(){downloads++;};
w.MediaRecorder=class {
 static isTypeSupported(){return true;}
 constructor(){this.state='inactive';recorders++;}
 start(){this.state='recording';}
 stop(){this.state='inactive';setTimeout(()=>{this.ondataavailable?.({data:new w.Blob(['synthetic-clip'])});this.onstop?.();},0);}
};
Object.defineProperty(w.navigator,'mediaDevices',{value:{getUserMedia:async()=>({getTracks:()=>[{stop(){stops++;}}],getVideoTracks:()=>[{getSettings:()=>({deviceId:'camera-A'})}]}),enumerateDevices:async()=>[{kind:'videoinput',deviceId:'camera-A',label:'Cámara A de prueba'},{kind:'videoinput',deviceId:'camera-B',label:'Cámara B de prueba'}]}});
const admin={id:'admin-id',name:'Administrador de prueba',username:'adminprueba',role:'admin',force_change:false};
const security={id:'security-id',name:'Seguridad de prueba',username:'seguridad1',role:'seguridad',force_change:false};
const calls=[];
w.fetch=async(url,options={})=>{calls.push([url,options]);const bearer=options.headers?.Authorization||options.headers?.authorization||'';const user=bearer.includes('security-session')?security:admin;let result;
 if(url==='/api/auth/status')result={setup_required:setup};
 else if(url==='/api/auth/setup'){setup=false;result={token:'admin-session',user:admin};}
 else if(url==='/api/auth/login'){const body=JSON.parse(options.body);result={token:body.username==='seguridad1'?'security-session':'admin-session',user:body.username==='seguridad1'?security:admin};}
 else if(url==='/api/auth/me')result=user;
 else if(url==='/api/auth/logout')result={logged_out:true};
 else if(url==='/api/status')result={residents:1,events:0,models_ready:true,pad_ready:true,retention_days:7,visits:{authorized_now:0,inside:0}};
 else if(url==='/api/residents')result=[{id:'resident-id',name:'Residente de prueba',unit:'LAB',building:'Prueba',consent_at:'2026-10-17T12:00:00Z'}];
 else if(url==='/api/passages')result={recorded:true,pad_check_passed:true,door_unlocked:false};
 else if(url==='/api/events')result=[];
 else if(url==='/api/cameras')result=[{id:'observation1',role:'observe',label:'Observación de prueba',status:'desconectada'}];
 else if(url.startsWith('/api/cameras/observation1/connect')||url.endsWith('/disconnect'))result={status:'ok'};
 else if(url.startsWith('/api/cameras/observation1/analyze'))result={boxes:[],face_count:2,width:640,height:480,mode:'detect'};
 else if(url.startsWith('/api/analyze'))result={boxes:[],face_count:1,width:640,height:480,mode:'recognize',recognized:true,message:'Coincidencia sintética',resident:{id:'resident-id',name:'Residente de prueba',unit:'LAB',building:'Prueba'},entry_allowed:true,pad:{passed:true,state:'apto',samples:3,required:3,message:'PAD simulado superado'},pass_token:'synthetic-test-pass',token_ttl_seconds:20};
 else if(url==='/api/access/reset')result={reset:true};
 else if(url==='/api/evaluation/pad/report')result={total_trials:0,sessions:[]};
 else if(url==='/api/evaluation/report')result={total_trials:0,sessions:[]};
 else if(url.startsWith('/api/visits?'))result={items:[],next_before:null};
 else if(url.startsWith('/api/restrictions?'))result={items:[],next_before:null};
 else if(url==='/api/users')result=[admin,security];
 else if(url.startsWith('/api/audit'))result={integrity:{valid:true,checked:0},items:[]};
 else throw new Error('Ruta no simulada: '+url);
 return {ok:true,status:200,json:async()=>result,headers:{get:()=>null}};
};
const tick=async()=>{for(let i=0;i<15;i++)await new Promise(r=>setTimeout(r,0));};
const submit=id=>doc.getElementById(id).dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
(async()=>{try{
 const script=doc.createElement('script');script.textContent=fs.readFileSync(path.join(root,'app.js'),'utf8');doc.body.append(script);await tick();
 assert(doc.getElementById('login-dialog').open);assert(!doc.getElementById('setup-fields').hidden);
 for(const [id,value]of Object.entries({'admin-token':'setup-test-key','setup-name':'Administrador de prueba','login-username':'adminprueba','login-password':'ClaveDePrueba123!','setup-confirm':'ClaveDePrueba123!'}))doc.getElementById(id).value=value;
 submit('login-form');await tick();assert(!doc.getElementById('login-dialog').open);assert(!doc.querySelector('[data-view="users"]').hidden);assert.match(doc.getElementById('operator-summary').textContent,/Administración/);
 doc.querySelector('[data-view="users"]').click();await tick();assert.match(doc.getElementById('users-list').textContent,/Seguridad de prueba/);
 assert(!doc.getElementById('resident-pin'));
 doc.querySelector('#camera-form [name="source"]').value='rtsp://secret-of-test';
 doc.getElementById('logout').click();await tick();assert(doc.getElementById('login-dialog').open);assert.equal(doc.getElementById('residents-body').children.length,0);assert.equal(doc.querySelector('#camera-form [name="source"]').value,'');
 doc.getElementById('login-username').value='seguridad1';doc.getElementById('login-password').value='ClaveDePrueba123!';submit('login-form');await tick();assert(!doc.getElementById('login-dialog').open);
 assert(doc.querySelector('[data-view="users"]').hidden);assert(doc.querySelector('[data-view="evaluation"]').hidden);assert(doc.getElementById('user-form').closest('.view').hidden);assert(doc.getElementById('camera-form').hidden);
 doc.getElementById('start-camera').click();await tick();assert.equal(doc.getElementById('local-device-select').options.length,3);
 w.present({boxes:[],width:640,height:480,face_count:1,recognized:false,mode:'recognize',message:'Posible foto',pad:{passed:false,state:'posible_presentacion',samples:0,required:3,message:'Revisar presencialmente'}});assert.match(doc.getElementById('pad-status-text').textContent,/Posible foto/);assert(doc.getElementById('confirm-entry').disabled);
 w.present({boxes:[],width:640,height:480,face_count:1,recognized:true,mode:'recognize',resident:{id:'resident-id',name:'Residente de prueba',building:'Prueba',unit:'LAB'},pad:{passed:true,state:'apto',samples:3,required:3,message:'PAD simulado superado'},entry_allowed:true,pass_token:'synthetic-test-pass',token_ttl_seconds:20});
 doc.getElementById('crossing-observed').checked=true;doc.getElementById('crossing-observed').dispatchEvent(new w.Event('change'));assert(!doc.getElementById('confirm-entry').disabled);
 doc.getElementById('confirm-entry').click();await tick();assert(calls.some(([url,options])=>url==='/api/passages'&&!('resident_pin' in JSON.parse(options.body))));
 doc.getElementById('start-clip').click();await tick();assert(doc.getElementById('start-clip').disabled);assert.equal(recorders,1);
 doc.getElementById('stop-clip').click();await tick();assert.equal(downloads,1);assert(!doc.getElementById('start-clip').disabled);
 doc.getElementById('stop-camera').click();await tick();assert(stops>0);
 doc.querySelector('#observation-grid button').click();await tick();assert(calls.some(([url])=>url.includes('/observation1/analyze?mode=detect')));assert.match(doc.querySelector('#observation-grid p').textContent,/Sin identificación/);
 doc.getElementById('start-camera').click();await tick();doc.getElementById('start-clip').click();await tick();assert.equal(recorders,2);
 doc.getElementById('logout').click();await tick();assert.equal(downloads,1);assert(doc.getElementById('login-dialog').open);
 console.log('PASS DOM simulado: configuración/login/logout, limpieza, roles, PAD pendiente/alerta/apto y acceso sin PIN, webcam, observación anónima, clip y descarte. No prueba renderer ni eficacia real del modelo PAD o cámaras.');
 }finally{w.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
