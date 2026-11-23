"""Measure the seeded local API over real HTTP (200 requests per route).

Start the API, then run: .venv/Scripts/python scripts/benchmark.py
Results contain no credentials. Times include HTTP, auth, queries and serialization.
"""
import argparse
import ast
import json
import platform
import statistics
import os
import subprocess
import sys
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]

def update_readme(result):
    c=result['counts']
    labels=[('Parts','parts'),('Revisions','revisions'),('Direct BOM lines across all revisions','bom_lines'),
            ('Engineering change requests','ecrs'),('API endpoints (method + path in OpenAPI)','api_endpoints'),
            ('Automated tests','tests'),('Backend source lines','backend_loc'),('Frontend source lines','frontend_loc')]
    rows=['| Measure | Result |','| --- | ---: |']+[f'| {label} | {c[key]:,} |' for label,key in labels]
    rows += [f"| Deepest BOM | {c['deepest_bom_child_edges']} child levels / {c['deepest_bom_child_edges']+1} tiers including the product |",
             f"| Generated 3D model designs | {c['unique_3d_models']} |",f"| Parts with released 3D attachments | {c['parts_with_3d']} |",
             '', '| Local API route | Requests | p50 | p95 |','| --- | ---: | ---: | ---: |']
    for label,key in [('BOM tree','bom-tree'),('Revision compare','compare'),('Dashboard','dashboard')]:
        t=result['latency_ms'][key]; rows.append(f"| {label} | {t['requests']} | {t['p50']:.2f} ms | {t['p95']:.2f} ms |")
    path=ROOT/'README.md'; before,tail=path.read_text(encoding='utf-8-sig').split('<!-- metrics:start -->',1); _,after=tail.split('<!-- metrics:end -->',1)
    path.write_text(before+'<!-- metrics:start -->\n'+'\n'.join(rows)+'\n<!-- metrics:end -->'+after,encoding='utf-8',newline='\n')

def percentile(values,p):
    values=sorted(values); rank=(len(values)-1)*p; low=int(rank); high=min(low+1,len(values)-1)
    return values[low]+(values[high]-values[low])*(rank-low)

def measure(base_url,requests):
    with httpx.Client(base_url=base_url,timeout=30) as client:
        login=client.post('/api/auth/login',json={'username':'engineer1','password':'password123'}); login.raise_for_status()
        client.headers['Authorization']='Bearer '+login.json()['access_token']
        def get(path):
            r=client.get(path); r.raise_for_status(); return r.json()
        parts=get('/api/parts'); changes=get('/api/changes')
        details=[get(f"/api/parts/{p['id']}") for p in parts]
        revisions=[r for p in details for r in p['revisions']]
        revision_details=[get(f"/api/revisions/{r['id']}") for r in revisions]
        attachments=[a for r in revisions for a in get(f"/api/revisions/{r['id']}/attachments")]
        trees=[get(f"/api/revisions/{r['id']}/bom-tree") for r in revisions]
        def depth(n): return max((1+depth(c) for c in n['children']),default=0)
        gearbox=next(p for p in details if p['part_number']=='GBX-001')
        old,new=gearbox['revisions'][0],gearbox['revisions'][-1]
        routes={'bom-tree':f"/api/revisions/{old['id']}/bom-tree",'compare':f"/api/revisions/{old['id']}/compare/{new['id']}",'dashboard':'/api/dashboard'}
        for path in routes.values():
            for _ in range(10): get(path)
        samples={name:[] for name in routes}
        for _ in range(requests):
            for name,path in routes.items():
                start=time.perf_counter_ns(); get(path); samples[name].append((time.perf_counter_ns()-start)/1e6)
        schema=get('/openapi.json')
    def loc(paths): return sum(len(p.read_text(encoding='utf-8-sig').splitlines()) for p in paths)
    backend=[p for p in (ROOT/'backend').rglob('*.py') if not any(x in p.parts for x in ('tests','__pycache__','.pytest_cache'))]
    frontend=[p for p in (ROOT/'frontend/src').rglob('*') if p.suffix in ('.ts','.tsx','.css')]
    tests=sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_') for p in (ROOT/'backend/tests').glob('test_*.py') for n in ast.walk(ast.parse(p.read_text(encoding='utf-8-sig'))))
    return {'measured_at_utc':datetime.now(timezone.utc).isoformat(),'environment':{'os':platform.system()+' '+platform.release(),'python':platform.python_version(),'base_url':base_url,'transport':'HTTP/1.1 loopback, sequential persistent client; 10 warmups per route','dataset':'Local seeded database, read through public API'},
      'counts':{'parts':len(parts),'revisions':len(revisions),'bom_lines':sum(len(r['bom_lines']) for r in revision_details),'ecrs':len(changes),'api_endpoints':sum(method in ('get','post','put','patch','delete','options','head') for path in schema['paths'].values() for method in path),'tests':tests,'backend_loc':loc(backend),'frontend_loc':loc(frontend),'deepest_bom_child_edges':max(map(depth,trees)),'unique_3d_models':len({a['filename'].split('-',2)[-1] for a in attachments if a['file_type']=='.stl' and '-demo.' not in a['filename']}),'parts_with_3d':len({r['part_id'] for r in revisions if any(a['revision_id']==r['id'] and a['file_type']=='.stl' for a in attachments)})},
      'loc_definition':'Physical lines including blanks/comments; backend/**/*.py excluding tests and caches; frontend/src/**/*.{ts,tsx,css}; scripts excluded.',
      'latency_ms':{name:{'path':routes[name],'requests':len(values),'p50':round(statistics.median(values),2),'p95':round(percentile(values,.95),2)} for name,values in samples.items()}}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--base-url',default='http://127.0.0.1:8000'); parser.add_argument('--requests',type=int,default=200); parser.add_argument('--output',type=Path,default=ROOT/'docs/benchmark.json'); parser.add_argument('--fresh-seed',action='store_true',help='Seed an isolated database twice and benchmark a temporary local API on port 8001'); parser.add_argument('--update-readme',action='store_true',help='Refresh the measured README tables from this run'); args=parser.parse_args()
    if args.requests<2: parser.error('--requests must be at least 2')
    process=None
    try:
        if args.fresh_seed:
            import sqlite3
            fixture=ROOT/'.local'/f'benchmark-{uuid.uuid4().hex}.db'; fixture.parent.mkdir(exist_ok=True)
            env={**os.environ,'DATABASE_URL':'sqlite:///'+fixture.as_posix()}
            def snapshot():
                with sqlite3.connect(fixture) as db:
                    tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                    return {name:db.execute(f'SELECT * FROM {name} ORDER BY id').fetchall() for name in tables}
            subprocess.run([sys.executable,'seed.py'],cwd=ROOT/'backend',env=env,check=True)
            first=snapshot()
            subprocess.run([sys.executable,'seed.py'],cwd=ROOT/'backend',env=env,check=True)
            assert first==snapshot(),'Second seed changed database rows'
            args.base_url='http://127.0.0.1:8001'
            # Fail if the port is occupied instead of benchmarking another process.
            import socket
            with socket.socket() as probe: probe.bind(('127.0.0.1',8001))
            log=(ROOT/'.local/benchmark-api.log').open('w',encoding='utf-8')
            process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
            for _ in range(100):
                if process.poll() is not None: raise RuntimeError('Benchmark API failed to start')
                try:
                    if httpx.get(args.base_url+'/api/health',timeout=1).is_success: break
                except httpx.TransportError: pass
                time.sleep(.2)
            else: raise RuntimeError('Benchmark API readiness timed out')
        result=measure(args.base_url,args.requests)
        if args.fresh_seed:
            result['environment']['dataset']='Fresh seed, isolated SQLite database; complete row snapshots identical after two runs'
            result['seed_idempotent']=True
        args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,indent=2))
        if args.update_readme: update_readme(result)
    finally:
        if process is not None:
            process.terminate(); process.wait(timeout=10); log.close()
