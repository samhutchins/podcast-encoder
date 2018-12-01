from subprocess import call
import zipfile
import os
import shutil


if os.path.isdir("build"):
    shutil.rmtree("build")

if os.path.isdir("dist"):
    shutil.rmtree("dist")

call(["pyinstaller", "encode-podcast.spec"])

with zipfile.ZipFile(os.path.join("dist", "encode-podcast.zip"), "w", zipfile.ZIP_DEFLATED) as f:
    abs_src = os.path.abspath(os.path.join("dist", "encode-podcast"))
    for root, dirs, files in os.walk(os.path.join("dist", "encode-podcast")):
        for file in files:
            abs_name = os.path.abspath(os.path.join(root, file))
            arc_name = abs_name[len(abs_src) + 1:]
            f.write(abs_name, arc_name)