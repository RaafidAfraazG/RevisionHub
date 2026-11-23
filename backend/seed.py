"""Idempotent bicycle + gearbox demo. python seed.py; existing edits are preserved."""

import sys

from datetime import datetime, timedelta, timezone

from pathlib import Path

from sqlalchemy import select

from app.database import Base, SessionLocal, engine

from app.auth import hash_password

from app.models import Attachment, AuditLog, BomLine, ChangeRequest, DecisionStage, Part, PartType, Revision, RevisionState, Role, User

from app.schemas import ChangeCreate, DecisionCreate

from app.services.audit import record_audit

from app.services.workflow import create_change, submit_change, decide_change

from app.routers.attachments import UPLOAD_DIR

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

from generate_models import generate

EPOCH=datetime(2026,8,3,9,tzinfo=timezone.utc)

MARKER='SHOWCASE_CATALOGUE_V1'

# Stable part numbers are also the migration keys for an existing demo database.

PARTS=[

('BIKE-001','City bicycle','A','700C commuter bicycle; 54 cm frame, mechanical disc brakes.'),

('WHL-100','Wheel assembly','A','32-spoke wheel, double-wall rim and sealed hub.'),

('RIM-101','Double-wall rim','C','6061-T6 rim; 622 mm bead seat, 19 mm internal width.'),

('SPK-102','Spoke, 290 mm','C','Butted stainless spoke; rolled M2 thread and J-bend head.'),

('TYR-103','City tyre, 700 × 35C','C','Puncture-protected tyre with reflective sidewall.'),

('FRM-200','Frame assembly','A','TIG-welded 4130 frame with replaceable routing hardware.'),

('BRK-300','Brake assembly','A','Cable-actuated caliper, rotor and hand lever.'),

('PAD-301','Organic brake pad','C','Resin friction material bonded to steel backing plate.'),

('LVR-302','Brake lever','C','Forged aluminium lever for mechanical disc brakes.'),

('HDL-400','Handlebar','C','6061-T6 riser bar, 640 mm width, 31.8 mm clamp.'),

('MNT-201','M5 mounting bolt','C','M5 × 12 stainless cap screw; 4 N·m torque.'),

('GDE-202','External cable guide','C','Nylon clip for 5 mm brake housing.'),

('GRM-203','Cable entry grommet','C','EPDM seal for internal cable routing.'),

('HUB-104','Hub and spoke carrier','A','100 mm OLD hub with six-bolt rotor interface.'),

('AXL-105','Hub axle','C','Hollow chromoly axle with M9 end threads.'),

('BRG-106','Hub bearing 6001','C','12 × 28 × 8 mm double-sealed deep groove bearing.'),

('NIP-107','Spoke nipple','C','14G brass nipple; nickel plated.'),

('TUB-108','Inner tube','C','Butyl 700C tube with 48 mm Presta valve.'),

('DSC-303','Slotted brake rotor','C','160 mm stainless rotor; 1.8 mm friction thickness.'),

('CAL-304','Brake caliper','C','Mechanical caliper with independent pad adjustment.'),

('CBL-305','Brake cable','C','1.5 mm stainless inner cable, pre-stretched.'),

('DRV-500','Drivetrain assembly','A','Single chainring drivetrain with cartridge bottom bracket.'),

('CRK-501','Crank arm','C','Forged 170 mm aluminium crank; square taper.'),

('CHN-502','Chain','C','114-link nickel-plated chain.'),

('SPR-503','Chainring','C','42-tooth steel chainring; 104 mm bolt circle.'),

('BBR-504','Bottom bracket bearing','C','Sealed cartridge bearing; 24 mm bore.'),

('PED-505','Pedal','C','Platform pedal with replaceable traction pins.'),

('STG-600','Steering assembly','A','Threadless headset, stem and fork.'),

('FRK-601','Rigid fork','C','4130 fork; 400 mm axle-to-crown.'),

('STM-602','Handlebar stem','C','90 mm stem with four-bolt faceplate.'),

('HST-603','Headset bearing','C','Sealed angular-contact bearing, 45 degree seat.'),

('GBX-001','Gearbox assembly','A','Spur reduction gearbox; 2:1 ratio, 25 N·m continuous output.'),

('GCS-100','Gear case assembly','A','Split housing with dowelled bearing seats.'),

('HSG-101','Lower housing','C','Machined aluminium case; H7 bearing bores.'),

('CVR-102','Inspection cover flange','C','Six-bolt cover flange with shaft clearance.'),

('GSK-103','Cover gasket','C','0.5 mm oil-resistant fibre gasket.'),

('DWL-104','Alignment dowel','C','6 × 20 mm hardened dowel; h6 tolerance.'),

('INS-200','Input shaft assembly','A','Input gear, shaft and paired bearings.'),

('GER-201','Input spur gear','C','28 teeth, module 2.5, 20 degree pressure angle; 20 mm bore.'),

('SFT-202','Input shaft','C','Ground 42CrMo4 shaft; keyed 20 mm journals.'),

('KEY-203','Parallel key','C','6 × 6 × 25 mm DIN 6885 key.'),

('GBR-204','Gearbox bearing','C','Double-sealed deep groove bearing; 20 mm bore.'),

('OUT-300','Output shaft assembly','A','Reduction gear, keyed shaft and bearing support.'),

('GER-301','Output spur gear','C','56-tooth reduction gear; case-hardened steel.'),

('SFT-302','Output shaft','C','30 mm keyed shaft with circlip groove.'),

('SEL-303','Radial shaft seal','C','NBR lip seal; 30 × 47 × 7 mm.'),

('MNT-400','Gearbox mounting assembly','A','Twin support brackets with vibration isolation.'),

('BKT-401','Chamfered mounting bracket','C','L bracket, 60 × 50 mm; relieved internal corner.'),

('BLT-402','M8 hex bolt','C','M8 × 35 grade 8.8 bolt; zinc plated.'),

('WSH-403','M8 washer','C','Hardened flat washer; 8.4 mm clearance.'),

('ISO-404','Isolation bush','C','70 Shore A elastomer bush with steel sleeve.')]

BOMS={

'BIKE-001':[('WHL-100',2),('FRM-200',1),('BRK-300',2),('STG-600',1),('DRV-500',1)],

'WHL-100':[('RIM-101',1),('SPK-102',32),('TYR-103',1),('HUB-104',1),('NIP-107',32),('TUB-108',1)],

'HUB-104':[('AXL-105',1),('BRG-106',2),('MNT-201',6)],

'FRM-200':[('MNT-201',4),('GDE-202',2)],

'BRK-300':[('PAD-301',2),('LVR-302',1),('DSC-303',1),('CAL-304',1),('CBL-305',1),('MNT-201',6)],

'DRV-500':[('CRK-501',2),('CHN-502',1),('SPR-503',1),('BBR-504',2),('PED-505',2),('MNT-201',4)],

'STG-600':[('FRK-601',1),('STM-602',1),('HST-603',2),('HDL-400',1),('MNT-201',4)],

'GBX-001':[('GCS-100',1),('INS-200',1),('OUT-300',1),('MNT-400',1),('BLT-402',4)],

'GCS-100':[('HSG-101',1),('CVR-102',1),('GSK-103',1),('DWL-104',2),('BLT-402',6),('WSH-403',6)],

'INS-200':[('GER-201',1),('SFT-202',1),('KEY-203',1),('GBR-204',2),('WSH-403',1)],

'OUT-300':[('GER-301',1),('SFT-302',1),('KEY-203',1),('GBR-204',2),('SEL-303',1),('WSH-403',1)],

'MNT-400':[('BKT-401',2),('BLT-402',4),('WSH-403',8),('ISO-404',4)]}

CHANGES=[

('FRM-200','review','Route rear brake cable through down tube','Remove external guides; add sealed grommets. Retain six M5 rack mounts.'),

('SPK-102','draft','Reduce wheel mass by 140 g','Replace steel spokes with aluminium. Validate 1,200 N tension and nipple compatibility.'),

('GER-201','passed','Increase input gear face width to 14 mm','Increase tooth contact area to address pitting at 25 N·m. Retain bore and keyway.'),

('CVR-102','rejected','Reduce cover flange thickness to 7 mm','Remove 2 mm from cover. Verify gasket compression and bolt preload.'),

('BKT-401','released','Relieve bracket inside corner','Add 4 mm corner relief for casting clearance. Break exposed edges by 1 mm.'),

('DSC-303','released','Add radial cooling slots to brake rotor','Add twelve slots to reduce temperature rise. Maintain 1.8 mm friction thickness.'),

('SEL-303','review','Change output shaft seal to FKM','Replace NBR with FKM for 120 °C oil compatibility. Verify lip drag on endurance rig.'),

('HUB-104','draft','Increase hub flange separation by 4 mm','Move spoke flanges outboard by 2 mm each. Confirm rotor-side clearance.'),

('GBR-204','rejected','Switch to low-friction bearing seals','Use non-contact seals to lower no-load torque. Submit ingress test results.'),

('RIM-101','released','Increase rim well wall to 1.6 mm','Increase spoke-bed thickness by 0.2 mm after 100,000-cycle fatigue test. Preserve bead seat.')]

MODEL_PARTS={'GER-201':'spur-gear','GER-301':'spur-gear','SPR-503':'spur-gear','CVR-102':'flange','HSG-101':'flange','RIM-101':'bike-rim','HUB-104':'hub-spokes','BKT-401':'bracket','BRG-106':'bearing','GBR-204':'bearing','BBR-504':'bearing','HST-603':'bearing','DSC-303':'brake-disc','BLT-402':'hex-bolt','MNT-201':'hex-bolt'}



def seed():

 Base.metadata.create_all(engine)

 with SessionLocal.begin() as db:

  users={}

  for username,name,role in [('engineer1','Alex Morgan',Role.ENGINEER),('reviewer1','Jordan Lee',Role.REVIEWER),('approver1','Taylor Chen',Role.APPROVER)]:

   u=db.scalar(select(User).where(User.username==username))

   if u is None:

    u=User(username=username,full_name=name,role=role,hashed_password=hash_password('password123')); db.add(u); db.flush()

   users[username]=u

  eng=users['engineer1']

  if not db.scalar(select(AuditLog.id).where(AuditLog.action==MARKER)):

   parts={}; revs={}

   def audit(actor,action,kind,id,when,**details):

    row=record_audit(db,actor,action,kind,id,source='showcase-v1',**details); row.timestamp=when

   for i,(number,name,kind,description) in enumerate(PARTS):

    p=db.scalar(select(Part).where(Part.part_number==number))

    if p is None:

     p=Part(part_number=number,name=name,part_type=PartType.ASSEMBLY if kind=='A' else PartType.COMPONENT,description=description,created_at=EPOCH+timedelta(minutes=i)); db.add(p); db.flush()

     audit(eng,'PART_CREATED','PART',p.id,p.created_at,part_number=number)

    parts[number]=p

    r=db.scalar(select(Revision).where(Revision.part_id==p.id,Revision.label=='A'))

    if r is None:

     r=Revision(part_id=p.id,label='A',state=RevisionState.RELEASED,change_note='Production baseline: '+description,created_at=EPOCH+timedelta(days=1),released_at=EPOCH+timedelta(days=5)); db.add(r); db.flush()

     audit(users['approver1'],'REVISION_RELEASED','REVISION',r.id,r.released_at,part_id=p.id,label='A',to_state='RELEASED')

    revs[number]=r

   def populate(r,children):

    for child,qty in children:

     if not db.scalar(select(BomLine.id).where(BomLine.parent_revision_id==r.id,BomLine.child_part_id==parts[child].id)):

      row=BomLine(parent_revision_id=r.id,child_part_id=parts[child].id,quantity=qty); db.add(row); db.flush()

      audit(eng,'BOM_LINE_ADDED','REVISION',r.id,r.created_at+timedelta(hours=2),part_id=r.part_id,child_part_id=parts[child].id,quantity=qty,line_id=row.id)

   for number,children in BOMS.items(): populate(revs[number],children)

   for number,children in BOMS.items():

    if number in {c[0] for c in CHANGES}: continue

    if db.scalar(select(Revision.id).where(Revision.part_id==parts[number].id,Revision.label=='B')): continue

    r=Revision(part_id=parts[number].id,label='B',state=RevisionState.DRAFT,change_note='Manufacturing review: update fastener quantities and assembly sequence.',created_at=EPOCH+timedelta(days=75)); db.add(r); db.flush()

    populate(r,[(c,q+2 if c in ('BLT-402','MNT-201') else q) for c,q in children]+([('GRM-203',2)] if number=='BIKE-001' else []))

    audit(eng,'REVISION_CREATED','REVISION',r.id,r.created_at,part_id=r.part_id,label='B',to_state='DRAFT')

   for number in ['TYR-103','PAD-301','HDL-400','AXL-105','NIP-107','CRK-501','CHN-502','FRK-601','STM-602','GSK-103']:

    a=revs[number]

    if len(parts[number].revisions)>1: continue

    a.state=RevisionState.OBSOLETE

    b=Revision(part_id=a.part_id,label='B',state=RevisionState.RELEASED,change_note='Supplier qualification complete; material certification and dimensional report accepted.',created_at=EPOCH+timedelta(days=25),released_at=EPOCH+timedelta(days=32)); db.add(b); db.flush()

    audit(users['approver1'],'REVISION_OBSOLETED','REVISION',a.id,b.released_at,part_id=a.part_id,to_state='OBSOLETE')

    audit(users['approver1'],'REVISION_RELEASED','REVISION',b.id,b.released_at,part_id=a.part_id,to_state='RELEASED')

   for i,(number,state,title,description) in enumerate(CHANGES):

    p=parts[number]; when=EPOCH+timedelta(days=82+i*2)

    if db.scalar(select(ChangeRequest.id).where(ChangeRequest.part_id==p.id)): continue

    before_create=db.scalar(select(AuditLog.id).order_by(AuditLog.id.desc()).limit(1)) or 0
    c=create_change(db,eng,ChangeCreate(part_id=p.id,title=title,reason=description.split('. ')[0]+'.',description=description))

    c.created_at=when; c.updated_at=when; r=c.draft_revision; r.created_at=when; r.change_note=description
    db.flush()
    for log in db.scalars(select(AuditLog).where(AuditLog.id>before_create)): log.timestamp=when

    if number in BOMS: populate(r,[('MNT-201',6),('GRM-203',2)] if number=='FRM-200' else BOMS[number])

    def stage(fn,hours):

     db.flush(); before=db.scalar(select(AuditLog.id).order_by(AuditLog.id.desc()).limit(1)) or 0

     fn(); db.flush(); db.refresh(c,attribute_names=['decisions'])

     for log in db.scalars(select(AuditLog).where(AuditLog.id>before)): log.timestamp=when+timedelta(hours=hours)

     c.updated_at=when+timedelta(hours=hours)

    if state!='draft': stage(lambda:submit_change(db,eng,c),2)

    if state in ('passed','released','rejected'):

     reject=state=='rejected'

     comment=('Flange deflection exceeds 0.08 mm seal limit. Restore thickness and attach preload analysis.' if number=='CVR-102' else 'Water ingress evidence missing. Run IP54 spray test for 30 minutes and attach inspection photos.') if reject else 'Tolerance stack, contact pattern and assembly clearance checked. Review passed.'

     stage(lambda:decide_change(db,users['reviewer1'],c,DecisionStage.REVIEW,DecisionCreate(decision='REJECT' if reject else 'APPROVE',comment=comment)),12)

    if state=='released':

     stage(lambda:decide_change(db,users['approver1'],c,DecisionStage.APPROVAL,DecisionCreate(decision='APPROVE',comment='Validation report accepted. Release for next batch; consume existing stock first.')),30)

     r.released_at=when+timedelta(hours=30)

    db.flush(); db.refresh(c,attribute_names=['decisions'])

    for d in c.decisions: d.created_at=when+timedelta(hours=12 if d.stage==DecisionStage.REVIEW else 30)

    for log in db.scalars(select(AuditLog).where(AuditLog.entity_type=='CHANGE_REQUEST',AuditLog.entity_id==c.id,AuditLog.action=='ECR_CREATED')): log.timestamp=when

   audit(eng,MARKER,'PART',parts['GBX-001'].id,EPOCH,catalogue='bicycle-and-gearbox')

  generate(UPLOAD_DIR)

  for number,model in MODEL_PARTS.items():

   p=db.scalar(select(Part).where(Part.part_number==number))

   r=db.scalar(select(Revision).where(Revision.part_id==p.id,Revision.state==RevisionState.RELEASED).order_by(Revision.id.desc()).limit(1))

   if r is None: continue

   stored=f'{number.lower()}-{r.label.lower()}-{model}.stl'; path=UPLOAD_DIR/stored

   if not path.exists(): path.write_bytes((UPLOAD_DIR/f'{model}.stl').read_bytes())

   if not db.scalar(select(Attachment.id).where(Attachment.stored_path==stored)):

    db.add(Attachment(revision_id=r.id,filename=f'{number}-{model}.stl',stored_path=stored,file_type='.stl',size=path.stat().st_size,uploaded_by=eng.id,uploaded_at=r.released_at or EPOCH))

 print('Bicycle and gearbox catalogue ready. Existing edits and decisions preserved.')

if __name__=='__main__': seed()

