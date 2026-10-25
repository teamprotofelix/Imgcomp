"""Real app UI + actual Worker; only picker/permission/filesystem are test doubles.
Files use in-memory fixtures, generated temporary input files, or isolated OPFS QA directories.
"""
import json, os, threading, http.server, functools, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
out=Path(os.environ.get('BROWSER_OUTPUT','work/browser'));out.mkdir(parents=True,exist_ok=True)
fixture=r'''() => {
 window.showDirectoryPicker=async()=>window.fx.root;
 const canvas=document.createElement('canvas');canvas.width=160;canvas.height=100;
 const c=canvas.getContext('2d');c.fillStyle='#aabbcc';c.fillRect(0,0,160,100);c.fillStyle='#123456';c.fillRect(10,10,50,70);
 return new Promise(resolve=>canvas.toBlob(async blob=>{
 const bytes=new Uint8Array(await blob.arrayBuffer());
 const fx=window.fx={removed:[],reads:{},mode:'ok',gate:null,release:null,logs:[],version:0};
 const handles=[0,1,2].map(i=>({kind:'file',name:`${i}.png`,isSameEntry:async other=>handles[i]===other&&!(fx.mode==='replace'&&i===1),getFile:async()=>{
  fx.reads[i]=(fx.reads[i]||0)+1;
  if(fx.mode==='fresh'&&i===1&&fx.reads[i]===3){fx.gate='fresh';await new Promise(r=>fx.release=r);}
  if(fx.mode==='scan'&&i===0){fx.gate='scan';await new Promise(r=>fx.release=r);}
  if(fx.mode==='missing'&&i===0)throw Error('missing');
  const b=bytes.slice();if((fx.mode==='keepChanged'&&i===0)||(fx.mode==='targetChanged'&&i===1))b[50]^=1;
  return new File(fx.chainBytes?[fx.chainBytes[i]]:fx.distinct?[b,new Uint8Array([i])]:fx.overlap&&i===0?[b,new Uint8Array([99])]:[b],`${i}.png`,{type:'image/png',lastModified:1000+i});
 }}));
 fx.root={name:'test-only',entries:async function*(){for(const h of handles)yield [h.name,h];},getFileHandle:async name=>handles[+name.split('.')[0]],requestPermission:async()=>{
  fx.reads={};if(fx.mode==='permission'){fx.gate='permission';await new Promise(r=>fx.release=r);}return fx.mode==='denied'?'denied':'granted';
 },removeEntry:async name=>{if(fx.mode==='partial'&&fx.removed.length)throw Error('test removal failure');fx.removed.push(name);if(fx.mode==='cancelPartial')document.getElementById('cancel').click();}};
 // Capture the actual downloadable audit, without changing app callbacks.
 const original=URL.createObjectURL;URL.createObjectURL=function(blob){if(blob.type==='application/json')blob.text().then(t=>fx.logs.push(JSON.parse(t)));return original.call(this,blob);};
 resolve();},'image/png'));
}'''
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium') or None,headless=True,args=['--no-sandbox'])
 context=browser.new_context(accept_downloads=True,viewport={'width':1365,'height':1000});page=context.new_page()
 def setup(distinct=False,count=3,overlap=False,chain=False):
  page.goto(base);page.evaluate(fixture.replace('[0,1,2]',f'Array.from({{length:{count}}},(_,i)=>i)'));page.evaluate('(x)=>{fx.distinct=x.distinct;fx.overlap=x.overlap}',{'distinct':distinct,'overlap':overlap});page.locator('#pick').click();
  if chain:
   page.evaluate('''async () => {fx.chainBytes=[];for(let i=0;i<3;i++){const c=document.createElement('canvas');c.width=9;c.height=8;const ctx=c.getContext('2d');for(let y=0;y<8;y++)for(let x=0;x<9;x++){let v=20+x*20;if(i>0&&y===i-1&&x<2)v=20+(1-x)*20;ctx.fillStyle=`rgb(${v},${v},${v})`;ctx.fillRect(x,y,1,1);}fx.chainBytes.push(new Uint8Array(await (await new Promise(r=>c.toBlob(r))).arrayBuffer()));}}''')
   page.locator('#threshold').evaluate("el=>{el.value='1';el.dispatchEvent(new Event('input'));}")
  if not distinct and not overlap and not chain:page.locator('#similarImages').uncheck()
  page.locator('#scan').click();page.wait_for_function(f"() => document.querySelector('#status').textContent.includes('내용 분석 성공 {count}개')")
  page.wait_for_function("() => document.querySelectorAll('.file-card img').length>0")
 def confirm(auto=True):
  if auto:page.locator('#auto').click()
  page.locator('#delete').click();page.locator('#ack').check();page.locator('#confirmText').fill('삭제')
 def finished():page.wait_for_function("() => !document.querySelector('#scan').disabled");page.wait_for_function('() => fx.logs.length>0')
 passed=[]
 for mode in ['missing','keepChanged','targetChanged','replace','denied','fresh','permission','partial','cancelPartial','ok']:
  setup()
  if mode in ['missing','keepChanged']:page.get_by_label('삭제 대상으로 선택: test-only/1.png',exact=True).check()
  confirm(mode not in ['missing','keepChanged'])
  page.evaluate('(mode)=>fx.mode=mode',mode);page.locator('#confirmDelete').click()
  if mode in ['fresh','permission']:
   page.wait_for_function('() => fx.gate!==null');assert page.locator('#scan').is_disabled();page.evaluate("() => document.querySelector('#scan').onclick()");page.locator('#cancel').click();page.evaluate('fx.release()')
  finished();data=page.evaluate('({removed:fx.removed,log:fx.logs.at(-1),status:document.querySelector("#status").textContent})')
  expected={'missing':0,'keepChanged':0,'targetChanged':1,'replace':1,'denied':0,'fresh':0,'permission':0,'partial':1,'cancelPartial':1,'ok':2}[mode]
  assert len(data['removed'])==expected,(mode,data)
  actions=data['log']['actions'];assert sum(a['status']=='deleted' for a in actions)==expected,(mode,data)
  if mode in ['fresh','permission']:assert all(a['status']=='unexecuted' for a in actions),data
  if mode=='partial':assert sum(a['status']=='blocked' for a in actions)==1,data
  if mode=='cancelPartial':assert sum(a['status']=='unexecuted' for a in actions)==1,data
  passed.append(mode)
 # Hidden selections remain in counts, frozen confirmation and actual execution.
 setup();page.locator('#auto').click();page.locator('#search').fill('no-match');assert page.locator('#selectionCount').inner_text()=='2개 선택';confirm(False)
 assert '전체 선택 2개' in page.locator('#confirmSummary').inner_text();assert 'test-only/1.png' in page.locator('#confirmList').inner_text();assert 'test-only/0.png' in page.locator('#confirmList').inner_text()
 page.screenshot(path=str(out/'confirm-desktop.png'),full_page=False);page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'confirm-mobile.png'),full_page=False);page.set_viewport_size({'width':1365,'height':1000});page.locator('#confirmDelete').click();finished();assert len(page.evaluate('fx.removed'))==2;passed.append('hidden selections + desktop/mobile confirmation')
 # Cancel while collecting, release stale await, then rescan through actual UI.
 setup();page.evaluate("fx.mode='scan'");page.locator('#scan').click();page.wait_for_function('() => fx.gate!==null');assert page.locator('#scan').is_disabled();page.evaluate("() => document.querySelector('#scan').onclick()");page.locator('#cancel').click();page.evaluate("fx.mode='ok';fx.release()");page.wait_for_function("() => !document.querySelector('#scan').disabled");page.locator('#scan').click();page.wait_for_function("() => document.querySelector('#status').textContent.includes('내용 분석 성공 3개')");assert page.locator('.file-card').count()==3;passed.append('cancel then rescan')
 # A changed plan after opening confirmation cannot be executed.
 setup();confirm();page.evaluate("document.querySelectorAll('.card-actions button')[2].click()");page.locator('#confirmDelete').click();assert page.evaluate('fx.removed')==[];assert '다시 확인' in page.locator('#status').inner_text();passed.append('confirmation plan mismatch rejected')
 # Read-only folder input uses actual app onchange and Worker.
 setup();readonly=Path(tempfile.mkdtemp(prefix='imgcomp-readonly-',dir=root/'work'));(readonly/'a.png').write_bytes(b'png test');(readonly/'b.png').write_bytes(b'png test');page.locator('#files').set_input_files(str(readonly));page.locator('#scan').click();page.wait_for_function("() => !document.querySelector('#scan').disabled");page.locator('#auto').click();assert page.locator('#delete').is_disabled();page.evaluate("() => document.querySelector('#confirmDelete').onclick()");assert page.evaluate('fx.removed')==[];passed.append('folder input read-only')
 # Actual similarity UI: no automatic selection, separate acknowledgement,
 # direct keep comparison and hidden selections shown in confirmation.
 setup(distinct=True);assert page.locator('#auto').is_disabled();assert page.locator('#selectionCount').inner_text()=='0개 선택'
 page.get_by_label('삭제 대상으로 선택: test-only/1.png',exact=True).check();confirm(False)
 assert '내용이 다른 파일일 수 있음' in page.locator('#confirmList').inner_text();assert page.locator('#confirmDelete').is_disabled();page.locator('#similarAck').check();assert page.locator('#confirmDelete').is_enabled()
 page.screenshot(path=str(out/'confirm-similar-desktop.png'),full_page=False);page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'confirm-similar-mobile.png'),full_page=False);page.set_viewport_size({'width':1365,'height':1000})
 page.get_by_role('button',name='돌아가기').click();page.locator('.file-card').nth(1).get_by_role('button',name='원본으로 남기기').click();assert page.locator('#selectionCount').inner_text()=='0개 선택';assert '직접 비교' in page.locator('#results').inner_text();passed.append('similarity acknowledgement + keep change')
 setup(chain=True);assert page.locator('.file-card').count()==3;page.get_by_label('삭제 대상으로 선택: test-only/2.png',exact=True).check();page.locator('.file-card').nth(1).get_by_role('button',name='원본으로 남기기').click();assert page.locator('#selectionCount').inner_text()=='0개 선택';assert page.get_by_label('삭제 대상으로 선택: test-only/2.png',exact=True).is_disabled();assert '유사 조건 불충족' in page.locator('.file-card').nth(2).inner_text();passed.append('nontransitive keep change revalidates actual decoded fingerprints')
 setup(overlap=True);page.locator('#auto').click();assert page.locator('#selectionCount').inner_text()=='1개 선택';page.evaluate("fx.mode='keepChanged'");confirm(False);page.locator('#similarAck').check();page.locator('#confirmDelete').click();finished();assert page.evaluate('fx.removed')==[];passed.append('overlap keep protection in real app')
 setup(count=100);assert page.locator('.file-card').count()==24;page.get_by_role('button',name='파일 24개 더 보기').click();assert page.locator('.file-card').count()==48;passed.append('large group bounded initial rendering')
 # Worker failure is surfaced, then an actual reanalysis succeeds.
 page.evaluate("() => {window.NativeWorker=Worker;window.Worker=class extends NativeWorker{constructor(url,options){super(new URL('/tests/failing-worker.js',location.href),options)}};}");page.locator('#scan').click();page.wait_for_function("() => !document.querySelector('#scan').disabled");page.wait_for_function("() => document.querySelector('#status').textContent.includes('실패 100개')");assert 'Worker' in page.locator('#warningList').text_content(),page.locator('#status').inner_text();page.evaluate('() => {window.Worker=window.NativeWorker;}');page.locator('#scan').click();page.wait_for_function("() => document.querySelector('#status').textContent.includes('내용 분석 성공 100개')");passed.append('Worker failure and retry')
 # Directory enumeration failure reports failure and permits rescan.
 page.evaluate("fx.root.entries=async function*(){throw Error('test folder read failure')}");page.locator('#scan').click();page.wait_for_function("() => !document.querySelector('#scan').disabled");assert 'test folder read failure' in page.locator('#status').inner_text();passed.append('folder read failure')
 # Sample mode: real app has no deletion call even when auto selected.
 page.locator('#demo').click();page.wait_for_function("() => !document.querySelector('#scan').disabled");page.locator('#auto').click();assert page.locator('#delete').is_disabled();passed.append('sample read-only')
 page.goto(base+'/tests/media-browser.html');page.wait_for_function("() => document.body.dataset.result",timeout=60000);assert page.locator('body').get_attribute('data-result')=='pass',page.locator('#output').inner_text();passed.append(page.locator('#output').inner_text())
 (out/'results.json').write_text(json.dumps(passed,ensure_ascii=False,indent=2));print(json.dumps(passed,ensure_ascii=False,indent=2));browser.close()
server.shutdown()
