from pathlib import Path
import zipfile

root=Path('/mnt/data/smart_wardrobe_erp_v1')
target=Path('/mnt/data/Smart_Wardrobe_ERP_V1_0_Phase1.zip')
files=[
    '.env.example','.gitignore','README.md','ROADMAP.md','Procfile',
    'START_SMART_WARDROBE_WINDOWS.bat','requirements.txt','railway.json',
    'app/__init__.py','app/db.py','app/main.py',
    'app/static/index.html','app/static/app.js','app/static/styles.css','app/static/favicon.svg',
    'data/.gitkeep','uploads/.gitkeep','tests/test_app.py'
]
previews={
    'PREVIEWS/DEMO_iPhone_Dashboard.png':'/mnt/data/smart_wardrobe_v1_iphone_dashboard.png',
    'PREVIEWS/DEMO_iPhone_2D_Wardrobe.png':'/mnt/data/smart_wardrobe_v1_iphone_layout.png',
    'PREVIEWS/DEMO_Desktop_Dashboard.png':'/mnt/data/smart_wardrobe_v1_desktop_preview.png',
    'PREVIEWS/DEMO_Desktop_2D_Wardrobe.png':'/mnt/data/smart_wardrobe_v1_layout_desktop_preview.png'
}
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as archive:
    for item in files:
        path=root/item
        if not path.exists():
            raise FileNotFoundError(path)
        archive.write(path,arcname='Smart_Wardrobe_ERP_V1_0/'+item)
    for rel,source in previews.items():
        archive.write(source,arcname='Smart_Wardrobe_ERP_V1_0/'+rel)
with zipfile.ZipFile(target) as archive:
    err=archive.testzip()
    assert err is None,err
    names=archive.namelist()
    assert all(not n.endswith('.sqlite3') for n in names)
    assert len(names)==len(files)+len(previews)
print('created:',target)
print('size:',target.stat().st_size)
print('files:',len(files)+len(previews))