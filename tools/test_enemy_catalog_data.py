"""Check that native visibility evidence and conservative UI labels stay distinct."""
import collections
from enemy_catalog_data import native_profiles,catalog_metadata,describe

def main():
    profiles=native_profiles()
    assert profiles,'Missing native actor audit data'
    verified=0;categories=collections.Counter()
    for (actor,variant),row in profiles.items():
        assert 0<actor<0x80 and actor!=0x2a,'Boss/controller accidentally included in ordinary audit'
        entry={'type':actor,'variant':variant,'room':row['room']}
        meta=catalog_metadata(entry)
        assert meta['native_verified']==row['visible_native_actor']
        assert describe(entry)['room']==entry['room'] and len(entry)==3,'Metadata must preserve spawn data'
        if row['visible_native_actor']:
            assert row['poses'] and row['matched_samples']>0 and row['image']
            verified+=1;categories[meta['category']]+=1
        else:
            assert not meta['verified'],'A descriptive label must never imply native visibility'
    for actor in (0x06,0x33,0x4d):
        assert catalog_metadata({'type':actor})['category']=='object'
    assert catalog_metadata({'type':0x7c,'variant':128})['category']=='hazard'
    assert catalog_metadata({'type':0x11})['category']=='enemy'
    assert catalog_metadata({'type':0x03})['category']=='unclassified'
    assert not catalog_metadata({'type':0x04})['native_verified']
    assert not catalog_metadata({'type':0x80})['native_verified']
    print(f'PASS: {len(profiles)} unique profiles; {verified} visibly verified; categories {dict(categories)}')
    print('PASS: native visibility, enemy identity, architecture, hazards and unverified candidates remain distinct')

if __name__=='__main__':main()
