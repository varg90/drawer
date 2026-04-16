from PyInstaller.archive.readers import CArchiveReader

a44 = CArchiveReader('d044.exe').toc

# Verify OpenGLWidgets present
openglw = [n for n in a44 if 'OpenGLWidgets' in n]
print("OpenGLWidgets files in v0.4.4:")
for n in openglw:
    print(f"  {n}")

# List all pyd files
pyds = sorted([n for n in a44 if n.endswith('.pyd')])
print(f"\n.pyd files in v0.4.4 ({len(pyds)}):")
for n in pyds:
    print(f"  {n}")

# Biggest files
entries = sorted([(n, v[1], v[2]) for n, v in a44.items()], key=lambda x: -x[2])
print(f"\nTop 30 largest in v0.4.4 (uncompressed):")
for n, c, u in entries[:30]:
    print(f"  {u/1024:>8.0f} KB  {n}")
