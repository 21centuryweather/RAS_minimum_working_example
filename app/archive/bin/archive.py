import os
import pathlib
import subprocess

ROOTDIR = os.getenv("ROOTDIR")
MASSROOTDIR = os.getenv("MASSROOTDIR")


for root, dirs, files in os.walk(ROOTDIR):

    # First make directory in mass
    rel_root = pathlib.Path(root).relative_to(pathlib.Path(ROOTDIR))
    mass_path = f"{MASSROOTDIR}/{str(rel_root).strip('.')}"
    my_command = ["moo", "mkdir", "-p", mass_path]
    r = subprocess.run(my_command)
    # 10 = directory already exists
    if r.returncode not in [0, 10]:
        print(r.args)
        print(r.stdout)
        print(r.stderr)
        raise Exception("moose mkdir command fail")

    # Identify text_files, as files ending in '.nl' (namelists), or starting with 'L' (a vertical levelset), or other text file we are expecting to be present.
    text_files = [
        f
        for f in files
        if f[0] == "L"
        or f.endswith(".nl")
        or f in ["ancil_filenames", "ancil_versions"]
    ]
    other_files = [f for f in files if f not in text_files]
    if text_files:
        # Put all text_files in a tarball, and archive the tarball
        my_command = ["tar", "-cf", "text_files.tar", "-C", root] + text_files
        r = subprocess.run(my_command, check=True)
        my_command = ["moo", "put", "-f", "text_files.tar", mass_path]
        r = subprocess.run(my_command, check=True)
    if other_files:
        # Archive ancil files that are not links
        fullpaths = [os.path.join(root, f) for f in other_files]
        not_links = [f for f in fullpaths if not os.path.islink(f)]
        my_command = ["moo", "put", "-f"] + not_links + [mass_path]
        r = subprocess.run(my_command, check=True)
