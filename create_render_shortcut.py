import os

desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
target = r"C:\Users\abhi's pc\.gemini\antigravity\scratch\vicy-cloud\push_to_render.bat"
sLinkFile = os.path.join(desktop, "Deploy VICY to Render.lnk")

vbs_content = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{sLinkFile}")
oLink.TargetPath = "{target}"
oLink.WorkingDirectory = "C:\\Users\\abhi's pc\\.gemini\\antigravity\\scratch\\vicy-cloud"
oLink.Description = "Deploy VICY to Render Cloud"
oLink.Save
'''

vbs_path = os.path.join(os.environ["TEMP"], "make_render_shortcut.vbs")
with open(vbs_path, "w", encoding="utf-8") as f:
    f.write(vbs_content)

os.system(f'cscript //nologo "{vbs_path}"')
print("Deploy to Render shortcut created:", os.path.exists(sLinkFile))
