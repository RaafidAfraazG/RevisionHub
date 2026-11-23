"""Capture the actual app with Playwright; assemble the gear animation with Pillow.

Install extras: pip install -r scripts/requirements.txt
Run with a seeded API and Vite: python scripts/capture_showcase.py
Uses installed Chrome or Playwright Chromium; never changes engineering records.
"""
import argparse
import io
import json
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def capture(base_url, animate=True):
    out=ROOT/'docs/screenshots'; out.mkdir(parents=True,exist_ok=True)
    qa=ROOT/'.local/browser-qa'; qa.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        chrome=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
        browser=p.chromium.launch(headless=True,executable_path=str(chrome) if chrome.exists() else None,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        errors=[]; page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base_url+'/login'); page.get_by_label('Username',exact=True).fill('engineer1'); page.get_by_label('Password',exact=True).fill('password123')
        page.screenshot(path=str(qa/'login.png'))
        page.get_by_role('button',name='Sign in',exact=True).click(); page.wait_for_url(base_url+'/')
        page.get_by_role('heading',name='Engineering overview').wait_for()
        page.evaluate('document.fonts.ready'); page.wait_for_timeout(700); page.screenshot(path=str(out/'dashboard-new.png'),full_page=True)
        token=page.evaluate("localStorage.getItem('revisionhub_token')")
        request=p.request.new_context(base_url=base_url,extra_http_headers={'Authorization':'Bearer '+token})
        def get(path):
            r=request.get('/api'+path); assert r.ok,(path,r.status); return r.json()
        parts=get('/parts'); by_number={part['part_number']:part for part in parts}
        def revision(number,state='RELEASED'):
            detail=get('/parts/'+str(by_number[number]['id'])); return next(r for r in reversed(detail['revisions']) if r['state']==state)
        checks=[]
        def visit(path,heading,filename=None,full=True):
            page.goto(base_url+path); page.get_by_role('heading',name=heading,exact=True).wait_for(); page.locator('.empty:has(.animate-spin)').wait_for(state='detached')
            page.evaluate('document.fonts.ready'); page.wait_for_timeout(700); page.screenshot(path=str(filename or qa/(path.strip('/').replace('/','-')+'.png')),full_page=full)
            assert not page.locator('[role="alert"]').count(),path
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Page overflow: {path}'
            checks.append(path)
        visit('/parts','Parts library')
        search=page.get_by_role('textbox',name='Search parts'); search.fill('GER-201'); page.wait_for_timeout(350); page.get_by_role('link',name='GER-201',exact=True).wait_for(); assert page.locator('tbody tr').count()==1
        visit('/parts/'+str(by_number['GBX-001']['id']),'Gearbox assembly')
        page.get_by_role('tab',name='Audit',exact=True).click(); page.screenshot(path=str(qa/'part-audit.png'),full_page=True)
        bike=revision('BIKE-001'); visit('/revisions/'+str(bike['id']),by_number['BIKE-001']['name']+' Rev '+bike['label'],out/'bom-tree.png',full=False)
        page.get_by_role('button',name='Collapse all',exact=True).click(); assert page.locator('.bom-table tbody tr').count()==1
        page.get_by_role('button',name='Expand all',exact=True).click(); assert page.locator('.bom-table tbody tr').count()>20
        frame=by_number['FRM-200']; visit('/parts/'+str(frame['id'])+'/compare','Compare revisions',out/'compare-diff.png')
        assert page.locator('.diff-table tbody tr').count()>=3
        visit('/changes','Change requests')
        visit('/inbox','My Inbox')
        visit('/changes/new','New Change Request')
        changes=get('/changes')
        for state in ('REJECTED','IN_REVIEW','RELEASED'):
            c=next(c for c in changes if c['status']==state)
            page.goto(base_url+'/changes/'+str(c['id'])); page.get_by_role('heading',name=c['title'],exact=True).wait_for()
            page.screenshot(path=str(out/'ecr-detail.png' if state=='REJECTED' else qa/f'ecr-{state.lower()}.png'),full_page=True); checks.append('/changes/'+str(c['id']))
        for number,name in [('GER-201','gear'),('CVR-102','flange'),('DSC-303','brake-disc'),('RIM-101','rim')]:
            rev=revision(number); page.goto(base_url+'/revisions/'+str(rev['id']))
            viewer=page.locator('.stl-viewer'); viewer.wait_for(); viewer.scroll_into_view_if_needed()
            viewer.get_by_role('button',name='Reset view').wait_for(); page.wait_for_function("!document.querySelector('.viewer-overlay') && !!document.querySelector('.viewer-metrics')")
            assert not page.locator('[role="alert"]').count()
            viewer.screenshot(path=str(out/f'viewer-{name}.png'))
            if name=='gear' and animate:
                page.screenshot(path=str(qa/'viewer-page.png'),full_page=True)
                rotate=viewer.get_by_role('button',name='Auto-rotate off',exact=True); rotate.click()
                frames=[]
                # Capture time-ordered WebGL frames from the running viewer.
                for _ in range(60):
                    page.wait_for_timeout(85)
                    frames.append(Image.open(io.BytesIO(viewer.screenshot())).convert('RGB'))
                assert frames[0].tobytes()!=frames[30].tobytes(),'Gear must rotate'
                frames[0].save(out/'viewer.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=True)
                viewer.get_by_role('button',name='Reset view').click(); assert viewer.get_by_role('button',name='Auto-rotate off').get_attribute('aria-pressed')=='false'
        # Check every primary view at phone width; table overflow stays inside its scroll container.
        page.set_viewport_size({'width':390,'height':844})
        for path in ['/','/parts','/changes','/inbox','/changes/new','/parts/'+str(frame['id'])+'/compare','/revisions/'+str(bike['id'])]:
            page.goto(base_url+path); page.wait_for_timeout(600)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Mobile overflow: {path}'
            page.screenshot(path=str(qa/('mobile-'+(path.strip('/').replace('/','-') or 'dashboard')+'.png')),full_page=True)
        # Role-specific queues and action panels, without mutating any request.
        page.set_viewport_size({'width':1440,'height':1000})
        for role in ('reviewer1','approver1'):
            page.get_by_role('button',name='Logout',exact=True).click(); page.get_by_label('Username',exact=True).fill(role); page.get_by_label('Password',exact=True).fill('password123'); page.get_by_role('button',name='Sign in',exact=True).click(); page.wait_for_url(lambda url: '/login' not in url); page.goto(base_url+'/')
            page.get_by_role('heading',name='Engineering overview').wait_for(); page.screenshot(path=str(qa/f'{role}-dashboard.png'),full_page=True)
            page.get_by_role('link',name='My inbox',exact=True).click(); page.get_by_role('heading',name='My Inbox',exact=True).wait_for(); page.locator('tbody tr').first.wait_for(); assert page.locator('tbody tr').count()>0
        browser.close()
        report={'pages':checks,'mobile_width':390,'roles':['ENGINEER','REVIEWER','APPROVER'],'runtime_errors':errors,'animation_frames':60}
        (qa/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        assert not errors,errors
        print(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--base-url',default='http://127.0.0.1:5173'); parser.add_argument('--skip-animation',action='store_true',help='Keep the existing GIF while rerunning page checks'); args=parser.parse_args(); capture(args.base_url,not args.skip_animation)
