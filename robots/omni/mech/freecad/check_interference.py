# Interference check over every part of every component occurrence in the assembly, worst first.
import time
from fusionflow import helpers as H
doc = App.getDocument("BugBot_Base"); asm = doc.getObject("Assembly")
t0 = time.time(); pairs, n = H.interference(asm)
result = {"pairs": pairs, "parts": n, "seconds": round(time.time() - t0, 1)}
