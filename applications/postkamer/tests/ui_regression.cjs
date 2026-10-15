// Exercises the shipped browser controller with an in-memory DOM/API.
// Node built-ins only; actual responsive layout is also measured in a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../maildemo/static/app.js'), 'utf8');
class Element {
  constructor() { this.value=''; this.textContent=''; this.children=[]; this.hidden=false; this.disabled=false; this.dataset={}; this.attrs={}; this.events={}; this.classes=new Set();
    this.classList={toggle:(name,on)=>on ? this.classes.add(name):this.classes.delete(name)}; }
  append(...nodes) {this.children.push(...nodes);}
  replaceChildren(...nodes) {this.children=nodes;}
  addEventListener(name,action) {this.events[name]=action;}
  setAttribute(name,value) {this.attrs[name]=value;}
  scrollIntoView() {} focus() {}
}
const flush = () => new Promise(resolve=>setImmediate(resolve));
async function harness() {
  const elements={};
  const get=id=>elements[id] ||= new Element();
  get('folder').value='inbox'; get('detail').hidden=true;
  const details=new Map([1,2,3].map(id=>[id,{id,category:id===3?'support':'info',folder:'inbox',sender:'contact@demo.test',recipient:'info@demo.test',subject:'Demo '+id,body:'Bericht '+id,received_at:'2026-01-01T00:00:00Z',summary:'Deterministisch voorbeeld',draft:'Concept '+id,draft_version:1,edited:0,preview:'Bericht '+id}]));
  const h={elements,get,details,confirm:true,confirmations:0,override:null};
  const context=vm.createContext({console,URLSearchParams,Intl,Date,Number,String,AbortSignal,setTimeout,clearTimeout,
    document:{getElementById:get,createElement:()=>new Element(),querySelectorAll:selector=>selector==='.message'?get('messages').children:[],querySelector:selector=>selector==='.message'?get('messages').children[0]:get('list-heading')},
    window:{confirm:()=>{h.confirmations++;return h.confirm;},addEventListener:()=>{}},
    fetch:async(url,options={})=>{
      if(h.override){const response=h.override(url,options);if(response)return response;}
      const parsed=new URL(url,'http://127.0.0.1:8765');
      let body;
      if(parsed.pathname==='/api/messages') {
        const q=parsed.searchParams.get('q'),category=parsed.searchParams.get('category');
        const items=[...details.values()].filter(m=>(!category || m.category===category) && (!q || m.subject.includes(q)));
        body={items,counts:{total:40,categories:{info:14,verkoop:14,support:12}}};
      } else {
        const id=Number(parsed.pathname.split('/')[3]);body=details.get(id);
        if(options.method==='PATCH') {
          const input=JSON.parse(options.body);
          if(input.version!==body.draft_version)return {ok:false,json:async()=>({error:'Conflict'})};
          body={...body,draft:input.text,draft_version:body.draft_version+1,edited:1};details.set(id,body);
        }
      }
      return {ok:true,json:async()=>({...body})};
    }});
  h.context=context;h.run=code=>vm.runInContext(code,context);vm.runInContext(source,context);await flush();return h;
}
const results=[];
async function test(name,fn){await fn();results.push(name);console.log('PASS '+name);}
(async()=>{
  await test('automatic first selection and visible original/summary/editor',async()=>{
    const h=await harness();assert.equal(h.run('current.id'),1);assert.equal(h.get('detail').hidden,false);
    assert.equal(h.get('body').textContent,'Bericht 1');assert.equal(h.get('summary').textContent,'Deterministisch voorbeeld');assert.equal(h.get('draft').value,'Concept 1');
  });
  await test('filter automatically selects matching first item',async()=>{
    const h=await harness();h.get('category').value='support';await h.run('loadList()');assert.equal(h.run('current.id'),3);assert.equal(h.get('messages').children.length,1);
  });
  await test('selection and unsaved text survive matching filter',async()=>{
    const h=await harness();h.get('draft').value='Niet opgeslagen';h.get('draft').events.input();h.get('category').value='info';await h.run('loadList()');
    assert.equal(h.run('current.id'),1);assert.equal(h.get('draft').value,'Niet opgeslagen');assert.equal(h.run('dirty'),true);
  });
  await test('zero results clear stale detail and show empty state',async()=>{
    const h=await harness();h.get('search').value='onvindbaar';await h.run('loadList()');assert.equal(h.run('current'),null);assert.equal(h.get('detail').hidden,true);
    assert.equal(h.get('empty').hidden,false);assert.equal(h.get('empty-title').textContent,'Geen berichten gevonden');assert.equal(h.get('save').disabled,true);
  });
  await test('zero results never discard unsaved draft; cancel keeps text',async()=>{
    const h=await harness();h.get('draft').value='Bewaar dit';h.get('draft').events.input();h.get('search').value='onvindbaar';await h.run('loadList()');
    assert.equal(h.get('draft').value,'Bewaar dit');assert.equal(h.run('current.id'),1);assert.match(h.get('list-status').textContent,/concept blijft open/);
    h.confirm=false;await h.run('openMail(2)');assert.equal(h.run('current.id'),1);assert.equal(h.confirmations,1);
  });
  await test('save persists edited draft and reopen reads saved version',async()=>{
    const h=await harness();h.get('draft').value='Opgeslagen edit';h.get('draft').events.input();await h.run('saveDraft()');
    assert.equal(h.details.get(1).draft,'Opgeslagen edit');assert.equal(h.run('dirty'),false);assert.equal(h.run('current.draft_version'),2);
    await h.run('openMail(2)');await h.run('openMail(1)');assert.equal(h.get('draft').value,'Opgeslagen edit');
  });
  await test('late detail response cannot cross newer filter',async()=>{
    const h=await harness();let release;
    h.override=url=>url==='/api/messages/2'?new Promise(resolve=>{release=resolve;}):null;
    const pending=h.run('openMail(2)');await flush();h.get('category').value='support';await h.run('loadList()');
    release({ok:true,json:async()=>h.details.get(2)});await pending;assert.equal(h.run('current.id'),3);assert.equal(h.get('subject').textContent,'Demo 3');
  });
  await test('late list response cannot replace newer filtered list',async()=>{
    const h=await harness();let release;
    h.override=url=>url.includes('q=slow')?new Promise(resolve=>{release=resolve;}):null;
    h.get('search').value='slow';const pending=h.run('loadList()');await flush();h.get('search').value='';h.get('category').value='support';await h.run('loadList()');
    release({ok:true,json:async()=>({items:[h.details.get(1)],counts:{total:40,categories:{info:14,verkoop:14,support:12}}})});await pending;
    assert.equal(h.run('current.id'),3);assert.equal(h.get('messages').children[0].dataset.id,3);
  });
  await test('overview and reset retain correct total and visible counts',async()=>{
    const h=await harness();h.get('category').value='support';await h.run('loadList()');
    assert.equal(h.get('stats').children[0].children[1].textContent,'40');assert.equal(h.get('stats').children[4].children[1].textContent,'1');
    h.get('clear-filters').events.click();await flush();assert.equal(h.get('category').value,'');assert.equal(h.get('messages').children.length,3);
  });
  console.log(JSON.stringify({result:'PASS',cases:results.length,tests:results}));
})().catch(error=>{console.error(error);process.exitCode=1;});
